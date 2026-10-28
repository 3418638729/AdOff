"""还原所有改动。

只还原 AdOff 自己做过的事情：
- 恢复被挂起的广告组件
- 移除电池优化白名单
- 可选卸载 AdAway
"""

from __future__ import annotations

from pathlib import Path

from . import adb as adbkit
from . import adaway, profiles, system


def restore_suspended(adb: Path, serial: str) -> list[str]:
    """把所有配置里列出、且当前确实处于挂起状态的包恢复。"""
    restored: list[str] = []
    for profile in profiles.list_profiles():
        for package in profile.suspend_packages:
            if system.is_installed(adb, serial, package) and system.is_suspended(adb, serial, package):
                if system.unsuspend(adb, serial, package):
                    restored.append(package)
    return restored


def restore_battery(adb: Path, serial: str) -> bool:
    return system.remove_battery_whitelist(adb, serial, adaway.PACKAGE)


def uninstall_adaway(adb: Path, serial: str) -> bool:
    """卸载 AdAway。调用前必须经过用户明确同意。"""
    result = adbkit.run(adb, "uninstall", adaway.PACKAGE, serial=serial, check=False)
    return "Success" in (result.stdout + result.stderr)


def full_report(adb: Path, serial: str, remove_app: bool = False) -> dict[str, object]:
    """执行完整还原并返回结果摘要。"""
    report: dict[str, object] = {}
    report["restored"] = restore_suspended(adb, serial)
    report["battery"] = restore_battery(adb, serial)
    report["uninstalled"] = uninstall_adaway(adb, serial) if remove_app else None
    return report
