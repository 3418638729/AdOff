"""命令行入口与交互菜单。"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from . import adb as adbkit
from . import adaway, hosts, profiles, restore, system, ui

REMOTE_DIR = "/sdcard/.xlDownload"
REMOTE_HOSTS = f"{REMOTE_DIR}/anti-ad.log"


def _load_adb(args: argparse.Namespace) -> Path:
    return adbkit.find_adb(args.adb)


def _load_device(adb: Path, args: argparse.Namespace) -> adbkit.Device:
    return adbkit.resolve_device(adb, args.serial)


# ---------------------------------------------------------------- 环境检查


def install_platform_tools() -> Path:
    """下载并解压 platform-tools 到项目目录。"""
    import platform
    import urllib.request

    system_name = platform.system()
    url = adbkit.PLATFORM_TOOLS_URL.get(system_name)
    if not url:
        raise adbkit.AdbError(f"暂不支持自动安装：{system_name}")

    ui.step("下载 Android platform-tools")
    archive = adbkit.PROJECT_ROOT / "platform-tools.zip"
    with urllib.request.urlopen(url, timeout=120) as response:
        archive.write_bytes(response.read())
    ui.ok(f"已下载 {archive.name}")

    ui.step("解压")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(adbkit.PROJECT_ROOT)
    archive.unlink()
    ui.ok(f"已解压到 {adbkit.LOCAL_PLATFORM_TOOLS}")
    return adbkit.find_adb()


def cmd_check(adb: Path, args: argparse.Namespace) -> int:
    ui.title("检查环境")
    ui.ok(f"adb：{adb}")

    devices = adbkit.list_devices(adb)
    if not devices:
        ui.fail("没有检测到手机")
        ui.info("检查数据线、USB 调试开关、手机上是否点了「允许」")
        return 1

    for device in devices:
        marked = adbkit.with_model(adb, device)
        if marked.online:
            ui.ok(f"{marked.serial}  型号：{marked.model or '未知'}")
        else:
            ui.warn(f"{marked.serial}  状态：{marked.state}（需要在手机上授权）")

    online = [d for d in devices if d.online]
    if not online:
        return 1

    device = adbkit.with_model(adb, online[0])
    profile = profiles.detect_profile(args.model or device.model)
    ui.info(f"匹配配置：{profile.name}")
    return 0


# ---------------------------------------------------------------- 去广告主流程


def _prepare_hosts(force: bool) -> tuple[Path, int]:
    ui.step("生成 hosts 规则")
    path, count = hosts.build(force_download=force)
    ui.ok(f"共 {count:,} 条规则 → {path}")
    return path, count


def _push_hosts(adb: Path, serial: str, local: Path) -> None:
    ui.step("推送到手机")
    adbkit.shell(adb, "mkdir", "-p", REMOTE_DIR, serial=serial, check=False)
    adbkit.push(adb, serial, local, REMOTE_HOSTS)
    ui.ok(f"已放到手机 {REMOTE_HOSTS}")


def _ensure_adaway(adb: Path, serial: str) -> None:
    ui.step("准备 AdAway")
    if adaway.is_installed(adb, serial):
        ui.ok("已安装，跳过")
        return
    ui.info("正在下载并安装，第一次可能要等几十秒")
    adaway.install(adb, serial)
    ui.ok("安装完成")


def _print_setup_steps() -> None:
    ui.step("在手机上完成最后几步")
    for index, line in enumerate(adaway.setup_steps(REMOTE_HOSTS), start=1):
        ui.info(f"{index}. {line}")


def _handle_suspend(adb: Path, serial: str, profile: profiles.Profile) -> None:
    if not profile.suspend_packages:
        return
    ui.step("系统广告组件")
    for package in profile.suspend_packages:
        if not system.is_installed(adb, serial, package):
            ui.info(f"{package} 不存在，跳过")
            continue
        if system.is_suspended(adb, serial, package):
            ui.ok(f"{package} 已处于挂起状态")
            continue
        if not ui.confirm(f"挂起 {package}？（可用「还原」恢复）"):
            ui.info("已跳过")
            continue
        if system.suspend(adb, serial, package):
            ui.ok(f"{package} 已挂起")
        else:
            ui.fail(f"{package} 挂起失败，可能被系统拒绝")


def _report_verify(result: dict[str, object]) -> bool:
    blocked = int(result["blocked"])
    total = int(result["total"])
    if not result["tunnel"]:
        ui.fail("VPN 隧道未建立（没有 tun0）")
        ui.info("打开 AdAway 后重新运行；清理后台会把 AdAway 的 VPN 断开")
    elif blocked == total:
        ui.ok(f"测试域名 {blocked}/{total} 全部被拦截")
    else:
        ui.warn(f"测试域名 {blocked}/{total} 被拦截，有 {total - blocked} 个仍能解析")
    return blocked == total and bool(result["tunnel"])


def cmd_block(adb: Path, args: argparse.Namespace) -> int:
    device = _load_device(adb, args)
    ui.title("开始去广告")
    ui.ok(f"设备：{device.serial}（{device.model or '型号未知'}）")

    model = args.model or device.model
    if not model:
        model = ui.ask("没读到型号，请手动输入（如 Redmi K70）")
    profile = profiles.detect_profile(model)
    ui.info(f"匹配配置：{profile.name}")
    for note in profile.notes:
        ui.info(f"· {note}")

    local_hosts, count = _prepare_hosts(force=args.refresh)
    _push_hosts(adb, device.serial, local_hosts)
    _ensure_adaway(adb, device.serial)
    adaway.keep_alive(adb, device.serial)
    ui.ok("已加入电池优化白名单")

    _print_setup_steps()
    _handle_suspend(adb, device.serial, profile)

    ui.step("验证")
    ui.info("请在手机上确认 AdAway 已经「应用」，然后回车继续")
    input()
    result = adaway.verify(adb, device.serial)
    passed = _report_verify(result)

    ui.title("完成")
    if passed:
        ui.ok(f"规则数 {count:,}，广告域名已被拦截")
    else:
        ui.warn("拦截还没完全生效，按上面的提示处理后重新运行 `verify`")
    return 0 if passed else 2


def cmd_verify(adb: Path, args: argparse.Namespace) -> int:
    device = _load_device(adb, args)
    ui.title("验证拦截效果")
    result = adaway.verify(adb, device.serial)
    for domain, resolved in dict(result["domains"]).items():
        if resolved:
            ui.warn(f"{domain} 仍能解析（未拦截）")
        else:
            ui.ok(f"{domain} 已拦截")
    return 0 if _report_verify(result) else 2


def cmd_restore(adb: Path, args: argparse.Namespace) -> int:
    device = _load_device(adb, args)
    ui.title("还原所有改动")
    remove_app = ui.confirm("同时卸载 AdAway？", default=False)
    if not ui.confirm("确认还原？", default=True):
        ui.info("已取消")
        return 0

    report = restore.full_report(adb, device.serial, remove_app=remove_app)
    restored = report["restored"]
    if restored:
        ui.ok(f"已恢复挂起：{'、'.join(restored)}")
    else:
        ui.info("没有需要恢复的挂起项")
    ui.ok("已移出电池优化白名单" if report["battery"] else "白名单移除失败")
    if report["uninstalled"] is True:
        ui.ok("AdAway 已卸载")
    elif report["uninstalled"] is False:
        ui.fail("AdAway 卸载失败，请手动卸载")
    return 0


# ---------------------------------------------------------------- 交互菜单


MENU = """
  AdOff — 安卓去广告

  1. 检查手机连接
  2. 输入手机型号
  3. 开始去广告
  4. 验证拦截效果
  5. 还原所有改动
  0. 退出
"""


def interactive(adb: Path, args: argparse.Namespace) -> int:
    model = args.model
    while True:
        print(ui.paint(MENU, "36"))
        choice = ui.ask("选择", "1")
        scoped = argparse.Namespace(**{**vars(args), "model": model})
        try:
            if choice == "1":
                cmd_check(adb, scoped)
            elif choice == "2":
                shown = f"当前：{model}" if model else "留空则读取手机上报的型号"
                entered = ui.ask(f"请输入手机型号（{shown}）", model)
                if entered:
                    model = entered
                    profile = profiles.detect_profile(model)
                    ui.ok(f"已记录：{model} → 匹配「{profile.name}」")
            elif choice == "3":
                return cmd_block(adb, scoped)
            elif choice == "4":
                cmd_verify(adb, scoped)
            elif choice == "5":
                cmd_restore(adb, scoped)
            elif choice == "0":
                return 0
            else:
                ui.warn("没有这个选项")
        except adbkit.AdbError as exc:
            ui.fail(str(exc))
        except (hosts.HostsError, adaway.AdAwayError) as exc:
            ui.fail(str(exc))
        except KeyboardInterrupt:
            print()
            return 130


# ---------------------------------------------------------------- 参数解析


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adoff",
        description="通过 adb + AdAway 在 Android 手机上做 DNS 层广告拦截",
    )
    parser.add_argument("--adb", help="adb 可执行文件路径")
    parser.add_argument("--serial", help="设备序列号（连了多台手机时必填）")
    parser.add_argument("--model", help="手机型号，例如 Redmi K70")
    parser.add_argument("--refresh", action="store_true", help="强制重新下载广告域名库")
    parser.add_argument("--install-adb", action="store_true", help="自动下载 Android platform-tools")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("check", help="只读检查：adb、设备、匹配到的配置")
    sub.add_parser("block", help="完整去广告流程")
    sub.add_parser("verify", help="检查广告域名是否真的被拦截")
    sub.add_parser("restore", help="还原所有改动")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.install_adb:
            adb = install_platform_tools()
            ui.ok(f"adb 已就绪：{adb}")
            return 0

        adb = _load_adb(args)

        if args.command == "check":
            return cmd_check(adb, args)
        if args.command == "block":
            return cmd_block(adb, args)
        if args.command == "verify":
            return cmd_verify(adb, args)
        if args.command == "restore":
            return cmd_restore(adb, args)
        return interactive(adb, args)

    except adbkit.AdbError as exc:
        ui.fail(str(exc))
        return 1
    except (hosts.HostsError, adaway.AdAwayError) as exc:
        ui.fail(str(exc))
        return 1
    except KeyboardInterrupt:
        print()
        return 130
