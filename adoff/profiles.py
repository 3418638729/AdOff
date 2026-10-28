"""手机型号配置。

DNS 拦截对任何安卓机都一样，型号只影响「系统自带的广告组件」怎么处理。
新增品牌只需要在 BUILTIN_PROFILES 里加一条。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Profile:
    """一个品牌/机型的处理配置。"""

    key: str
    name: str
    keywords: tuple[str, ...]
    suspend_packages: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def matches(self, model: str) -> bool:
        text = model.strip().lower()
        if not text:
            return False
        return any(keyword in text for keyword in self.keywords)


BUILTIN_PROFILES: tuple[Profile, ...] = (
    Profile(
        key="xiaomi",
        name="小米 / 红米（HyperOS、MIUI）",
        keywords=("redmi", "xiaomi", "小米", "红米", "hyperos", "miui"),
        suspend_packages=("com.miui.systemAdSolution",),
        notes=(
            "系统广告组件 com.miui.systemAdSolution 可以挂起，挂起前会单独询问。",
            "快应用框架 com.miui.hybrid 默认不动，挂了可能影响部分小程序。",
        ),
    ),
    Profile(
        key="generic",
        name="通用安卓",
        keywords=("android", "安卓"),
        notes=(
            "DNS 拦截对所有安卓机都有效。",
            "这个品牌的系统广告开关没有实测过，脚本不会去改系统设置。",
        ),
    ),
)

DEFAULT_PROFILE = BUILTIN_PROFILES[-1]

MODEL_HINTS = (
    "红米 K70 / Redmi K70 / 23113RKC6C",
    "红米 K60 / Redmi K60",
    "小米 14 / Xiaomi 14",
    "或者直接回车，让脚本读取手机上报的型号",
)


def detect_profile(model: str) -> Profile:
    """按型号文字挑配置，没匹配上返回通用配置。"""
    for profile in BUILTIN_PROFILES:
        if profile.matches(model):
            return profile
    return DEFAULT_PROFILE


def get_profile(key: str) -> Profile | None:
    return next((p for p in BUILTIN_PROFILES if p.key == key), None)


def list_profiles() -> list[Profile]:
    return list(BUILTIN_PROFILES)
