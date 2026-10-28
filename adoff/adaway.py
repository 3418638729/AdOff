"""AdAway 的下载、安装、保活与拦截效果验证。"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from . import adb as adbkit
from . import system

PACKAGE = "org.adaway"
BUILD_DIR = Path(__file__).resolve().parent.parent / "build"
APK_CACHE = BUILD_DIR / "AdAway.apk"

RELEASE_API = "https://api.github.com/repos/AdAway/AdAway/releases/latest"
DOWNLOAD_TIMEOUT = 120

# 用几个稳定的广告域名验证，全部解析失败才算拦截生效
TEST_DOMAINS = (
    "gdt.qq.com",
    "pgdt.gtimg.cn",
    "ad.oceanengine.com",
    "alimama.com",
)


class AdAwayError(RuntimeError):
    """AdAway 安装或配置失败。"""


def download_apk(force: bool = False) -> Path:
    """下载最新版 AdAway APK 到本地缓存。"""
    if APK_CACHE.exists() and not force:
        return APK_CACHE

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(RELEASE_API, headers={"User-Agent": "AdOff/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            release = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise AdAwayError(
            "获取 AdAway 下载地址失败，可能是网络问题。\n"
            "你可以手动下载 APK 放到 build/AdAway.apk，再重新运行。"
        ) from exc

    apk_url = next(
        (asset["browser_download_url"] for asset in release.get("assets", [])
         if asset["name"].endswith(".apk")),
        None,
    )
    if not apk_url:
        raise AdAwayError("最新 release 里没有找到 APK 文件")

    with urllib.request.urlopen(apk_url, timeout=DOWNLOAD_TIMEOUT) as response:
        APK_CACHE.write_bytes(response.read())
    return APK_CACHE


def is_installed(adb: Path, serial: str) -> bool:
    return system.is_installed(adb, serial, PACKAGE)


def install(adb: Path, serial: str, apk: Path | None = None) -> str:
    """安装或覆盖安装 AdAway。"""
    source = apk or download_apk()
    if not source.exists():
        raise AdAwayError(f"APK 不存在：{source}")
    return adbkit.install(adb, serial, source)


def keep_alive(adb: Path, serial: str) -> bool:
    """把 AdAway 加进电池优化白名单。

    小米/红米还需要手动开「自启动」和「省电策略 → 无限制」，
    这两项没有可靠的 adb 接口，界面层会提示用户。
    """
    return system.whitelist_from_battery(adb, serial, PACKAGE)


def relaunch(adb: Path, serial: str) -> None:
    """强制重启 AdAway，让 VPN 隧道重建。"""
    system.force_stop(adb, serial, PACKAGE)
    system.launch(adb, serial, PACKAGE)


def verify(adb: Path, serial: str) -> dict[str, object]:
    """检查拦截是否真的生效，返回逐项结果。"""
    results: dict[str, object] = {}
    results["process"] = is_installed(adb, serial)
    results["tunnel"] = adbkit.has_tun(adb, serial)
    domains = {domain: adbkit.resolves(adb, serial, domain) for domain in TEST_DOMAINS}
    results["domains"] = domains
    results["blocked"] = sum(1 for resolved in domains.values() if not resolved)
    results["total"] = len(domains)
    return results


def setup_steps(hosts_remote: str) -> list[str]:
    """AdAway 里添加本地来源的步骤。

    没有 root 就没有可靠的接口写它的配置，只能引导用户在界面上点。
    """
    return [
        "打开 AdAway，等待首次启动完成",
        "点底部「添加来源」按钮（+）",
        "标签填：AdOff",
        "类型选「文件」",
        "位置选：内部存储 → .xlDownload → anti-ad.log",
        f"确认后返回，规则数应在 10 万条以上（文件推到了 {hosts_remote}）",
        "回到主页，点「应用」或「更新」按钮",
        "看到「已成功更新 VPN 配置」即完成",
    ]
