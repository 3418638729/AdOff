"""生成 AdAway 能识别的 hosts 文件。

AdAway 只接受标准 hosts 格式（每行 `0.0.0.0 域名`），
纯域名列表和 Adblock 语法都会被解析成 0 条，所以这里统一转换。
"""

from __future__ import annotations

import re
import urllib.request
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BUILD_DIR = PROJECT_ROOT / "build"
EXTRA_DOMAINS = DATA_DIR / "sdk-domains.txt"
CACHE_FILE = BUILD_DIR / "anti-ad-domains.raw"
OUTPUT_FILE = BUILD_DIR / "anti-ad.hosts"

ANTI_AD_URL = (
    "https://cdn.jsdelivr.net/gh/privacy-protection-tools/anti-AD@master/anti-ad-domains.txt"
)
ANTI_AD_FALLBACK = (
    "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-domains.txt"
)

DOMAIN_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$")
DOWNLOAD_TIMEOUT = 60


class HostsError(RuntimeError):
    """下载或生成 hosts 失败。"""


def _download(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "AdOff/1.0"})
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def download_source(force: bool = False) -> Path:
    """下载 anti-AD 域名库到本地缓存，已有缓存且未强制刷新时直接复用。"""
    if CACHE_FILE.exists() and not force:
        return CACHE_FILE

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for url in (ANTI_AD_URL, ANTI_AD_FALLBACK):
        try:
            text = _download(url)
            CACHE_FILE.write_text(text, encoding="utf-8")
            return CACHE_FILE
        except Exception as exc:  # 网络问题换下一个镜像
            last_error = exc

    if CACHE_FILE.exists():
        return CACHE_FILE
    raise HostsError(f"下载 anti-AD 名单失败：{last_error}") from last_error


def read_extra_domains() -> list[str]:
    """读取项目自带的手工补充域名（广告 SDK 核心域名）。"""
    if not EXTRA_DOMAINS.exists():
        return []
    domains: list[str] = []
    for line in EXTRA_DOMAINS.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if DOMAIN_PATTERN.match(value):
            domains.append(value)
    return domains


def parse_domains(text: str) -> list[str]:
    """从 anti-AD 原始文本里取出合法域名，保持顺序并去重。"""
    seen: set[str] = set()
    domains: list[str] = []
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith(("#", "!", "[")):
            continue
        value = value.split()[0]
        if not DOMAIN_PATTERN.match(value):
            continue
        if value in seen:
            continue
        seen.add(value)
        domains.append(value)
    return domains


def build(force_download: bool = False) -> tuple[Path, int]:
    """生成 hosts 文件，返回（路径, 规则条数）。"""
    source = download_source(force=force_download)
    domains = parse_domains(source.read_text(encoding="utf-8", errors="replace"))
    if not domains:
        raise HostsError("anti-AD 名单解析出 0 条域名，文件可能已损坏，请加 --refresh 重试")

    extra = read_extra_domains()
    merged = list(dict.fromkeys(domains + extra))

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AdOff 生成的 hosts 文件",
        f"# 生成日期：{date.today().isoformat()}",
        f"# 来源：{ANTI_AD_URL}",
        f"# 规则数：{len(merged)}",
    ]
    lines += [f"0.0.0.0 {domain}" for domain in merged]
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return OUTPUT_FILE, len(merged)
