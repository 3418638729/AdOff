"""终端输出与交互。不依赖第三方库。"""

from __future__ import annotations

import os
import sys

if os.name == "nt":  # Windows 10+ 需要显式开启 ANSI
    os.system("")


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


_COLOR = _supports_color()


def paint(text: str, code: str) -> str:
    if not _COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def title(text: str) -> None:
    print()
    print(paint("=" * 52, "36"))
    print(paint(f"  {text}", "1;36"))
    print(paint("=" * 52, "36"))


def step(text: str) -> None:
    print(paint(f"\n▶ {text}", "1"))


def ok(text: str) -> None:
    print(f"  {paint('✓', '32')} {text}")


def warn(text: str) -> None:
    print(f"  {paint('!', '33')} {text}")


def fail(text: str) -> None:
    print(f"  {paint('✗', '31')} {text}")


def info(text: str) -> None:
    print(f"    {text}")


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"\n{prompt}{suffix}: ").strip()
    return value or default


def confirm(prompt: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    value = input(f"\n{prompt} [{hint}]: ").strip().lower()
    if not value:
        return default
    return value in ("y", "yes", "是", "好")
