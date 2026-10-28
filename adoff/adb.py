"""adb 的定位、调用与设备信息读取。

所有 adb 命令都经过这里，保证：
- 多设备时永远带 -s <序列号>
- 超时和退出码统一处理
- Windows / macOS / Linux 路径一致
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_PLATFORM_TOOLS = PROJECT_ROOT / "platform-tools"

PLATFORM_TOOLS_URL = {
    "Windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "Darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    "Linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
}

DEFAULT_TIMEOUT = 30


class AdbError(RuntimeError):
    """adb 找不到、执行失败，或设备状态不对。"""


@dataclass(frozen=True)
class Device:
    """一台已连接的设备。"""

    serial: str
    state: str
    model: str = ""

    @property
    def online(self) -> bool:
        return self.state == "device"


def adb_binary_name() -> str:
    return "adb.exe" if platform.system() == "Windows" else "adb"


def find_adb(explicit: str | None = None) -> Path:
    """按 显式参数 → 环境变量 → PATH → 项目自带 的顺序查找 adb。"""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("ADB"):
        candidates.append(Path(os.environ["ADB"]).expanduser())
    from_path = shutil.which("adb")
    if from_path:
        candidates.append(Path(from_path))
    candidates.append(LOCAL_PLATFORM_TOOLS / adb_binary_name())

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise AdbError(
        "找不到 adb。请任选一种：\n"
        "  1. 运行 `python adoff.py --install-adb` 自动下载\n"
        "  2. 手动下载 Android platform-tools，把 adb 加进 PATH\n"
        "  3. 设置环境变量 ADB 指向 adb 可执行文件"
    )


def run(
    adb: Path,
    *args: str,
    serial: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """执行一条 adb 命令，返回完整结果。"""
    command = [str(adb)]
    if serial:
        command += ["-s", serial]
    command += list(args)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise AdbError(f"adb 命令超时（{timeout} 秒）：{' '.join(args)}") from exc

    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise AdbError(f"adb 命令失败：{' '.join(args)}\n{detail}")
    return result


def shell(
    adb: Path,
    *args: str,
    serial: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    check: bool = True,
) -> str:
    """在设备上执行 shell 命令，返回去掉首尾空白的输出。"""
    result = run(adb, "shell", *args, serial=serial, timeout=timeout, check=check)
    return result.stdout.strip()


def list_devices(adb: Path) -> list[Device]:
    """列出 adb 看得见的设备（含未授权、离线）。"""
    output = run(adb, "devices", check=False).stdout
    devices: list[Device] = []
    for line in output.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        devices.append(Device(serial=parts[0], state=parts[1]))
    return devices


def with_model(adb: Path, device: Device) -> Device:
    """补上设备型号，读不到就保持原样。"""
    if not device.online:
        return device
    model = shell(adb, "getprop", "ro.product.model", serial=device.serial, check=False)
    return Device(serial=device.serial, state=device.state, model=model.strip())


def resolve_device(adb: Path, serial: str | None = None) -> Device:
    """选出一台可用设备；多台且没指定序列号时报错，由界面层询问。"""
    devices = list_devices(adb)
    if not devices:
        raise AdbError(
            "没有检测到手机。请检查：\n"
            "  1. 数据线是否连接\n"
            "  2. 手机上「开发者选项 → USB 调试」是否打开\n"
            "  3. 手机弹窗是否点了「允许」"
        )

    if serial:
        matched = next((d for d in devices if d.serial == serial), None)
        if matched is None:
            raise AdbError(f"找不到序列号为 {serial} 的设备")
        if not matched.online:
            raise AdbError(f"设备 {serial} 状态是 {matched.state}，请先在手机上授权")
        return with_model(adb, matched)

    online = [d for d in devices if d.online]
    if not online:
        states = "、".join(f"{d.serial}({d.state})" for d in devices)
        raise AdbError(f"设备未授权或离线：{states}\n请在手机弹窗上勾选「始终允许」并点「允许」。")
    if len(online) > 1:
        serials = "、".join(d.serial for d in online)
        raise AdbError(f"检测到多台设备（{serials}），请用 --serial 指定一台")
    return with_model(adb, online[0])


def push(adb: Path, serial: str, local: Path, remote: str) -> None:
    """把本地文件推到设备。remote 用设备上的正斜杠路径。"""
    run(adb, "push", str(local), remote, serial=serial, timeout=120)


def install(adb: Path, serial: str, apk: Path) -> str:
    """安装 APK，返回 adb 的输出（成功时通常是 Success）。"""
    result = run(adb, "install", "-r", str(apk), serial=serial, timeout=300, check=False)
    output = (result.stdout + result.stderr).strip()
    if "Success" not in output and result.returncode != 0:
        raise AdbError(f"安装失败：{output}")
    return output


def has_tun(adb: Path, serial: str) -> bool:
    """检查 VPN 隧道是否真的建立。

    AdAway 进程活着不代表 VPN 活着，只有 tun0 网卡存在才算数。
    """
    output = shell(adb, "ip", "addr", "show", serial=serial, check=False)
    return "tun0" in output


def resolves(adb: Path, serial: str, domain: str) -> bool:
    """域名能否解析成功。被拦截时返回 False。"""
    result = run(adb, "shell", "ping", "-c", "1", "-W", "1", domain, serial=serial, check=False)
    combined = result.stdout + result.stderr
    return "unknown host" not in combined.lower() and "bad address" not in combined.lower()
