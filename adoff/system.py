"""系统层面的处理：挂起广告组件、保活设置、状态检查。

只做可以还原的改动：
- 挂起用 pm suspend，对应的还原是 pm unsuspend
- 保活用 Doze 白名单，对应的还原是 whitelist -
绝不卸载、不 disable-user、不动系统分区。
"""

from __future__ import annotations

from pathlib import Path

from . import adb as adbkit


def is_installed(adb: Path, serial: str, package: str) -> bool:
    output = adbkit.shell(adb, "pm", "path", package, serial=serial, check=False)
    return "package:" in output


def is_suspended(adb: Path, serial: str, package: str) -> bool:
    """挂起状态在 dumpsys 里体现为 suspended=true。"""
    output = adbkit.shell(
        adb, "dumpsys", "package", package, serial=serial, check=False, timeout=60
    )
    return "suspended=true" in output


def suspend(adb: Path, serial: str, package: str) -> bool:
    """挂起一个包。返回 True 表示成功。"""
    result = adbkit.run(adb, "shell", "pm", "suspend", package, serial=serial, check=False)
    return result.returncode == 0 and is_suspended(adb, serial, package)


def unsuspend(adb: Path, serial: str, package: str) -> bool:
    result = adbkit.run(adb, "shell", "pm", "unsuspend", package, serial=serial, check=False)
    return result.returncode == 0


def whitelist_from_battery(adb: Path, serial: str, package: str) -> bool:
    """把 App 加进电池优化白名单，减少被系统冻结的概率。"""
    result = adbkit.run(
        adb, "shell", "dumpsys", "deviceidle", "whitelist", f"+{package}",
        serial=serial, check=False,
    )
    return result.returncode == 0


def remove_battery_whitelist(adb: Path, serial: str, package: str) -> bool:
    result = adbkit.run(
        adb, "shell", "dumpsys", "deviceidle", "whitelist", f"-{package}",
        serial=serial, check=False,
    )
    return result.returncode == 0


def is_battery_whitelisted(adb: Path, serial: str, package: str) -> bool:
    output = adbkit.shell(adb, "dumpsys", "deviceidle", "whitelist", serial=serial, check=False)
    return package in output


def force_stop(adb: Path, serial: str, package: str) -> None:
    adbkit.run(adb, "shell", "am", "force-stop", package, serial=serial, check=False)


def launch(adb: Path, serial: str, package: str) -> bool:
    """从桌面启动 App，比 am start 指定 Activity 更稳。"""
    result = adbkit.run(
        adb, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1",
        serial=serial, check=False,
    )
    return result.returncode == 0
