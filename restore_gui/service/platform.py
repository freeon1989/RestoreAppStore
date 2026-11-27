"""Определение платформы приложения: iOS/iPadOS или только Mac."""
from __future__ import annotations

MAC_KINDS = {
    "mac-software", "macsoftware", "desktop-software", "mac app", "macos",
}
MAC_PLATFORMS = ("macos", "osx", "os x", "mac os", "software-platform.macos")


def is_mac(item_or_platform) -> bool:
    if isinstance(item_or_platform, dict):
        return from_metadata(item_or_platform) == "mac"
    return str(item_or_platform or "").strip().lower() == "mac"


def from_metadata(item: dict | None) -> str:
    """Вернуть 'mac', 'ios' или '' по данным iTunes / ipatool."""
    if not isinstance(item, dict):
        return ""
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    sources = (item, raw)
    for src in sources:
        kind = str(src.get("storeKind") or src.get("kind") or "").strip().lower()
        if kind in MAC_KINDS or kind.replace(" ", "-") in MAC_KINDS:
            return "mac"
        for key in (
            "software-platform", "softwarePlatform", "platform",
            "deviceType", "device-type", "productType",
        ):
            value = str(src.get(key) or "").strip().lower()
            if any(token in value for token in MAC_PLATFORMS) or value in {"mac", "macosx"}:
                return "mac"
            if value in {"ios", "iphone", "ipad", "ipod", "iphoneos", "ipados", "software"}:
                return "ios"
        devices = src.get("supportedDevices") or src.get("devices") or []
        if isinstance(devices, list) and devices:
            text = " ".join(str(item) for item in devices)
            if devices and all(_is_mac_device(d) for d in devices):
                return "mac"
            if any(token in text for token in ("iPhone", "iPad", "iPod", "iOS")):
                return "ios"
    kind = str(item.get("kind") or "").strip().lower()
    if kind == "software":
        return "ios"
    return ""


def from_plist(data: dict | None) -> str:
    if not isinstance(data, dict):
        return ""
    platform = str(data.get("DTPlatformName") or data.get("DTPlatform") or "").strip().lower()
    if platform.startswith("macos") or platform in {"macosx", "osx"}:
        return "mac"
    if platform.startswith("iphone") or platform.startswith("ipad") or platform in {"iphoneos", "ipados", "ios"}:
        return "ios"
    if data.get("LSRequiresIPhoneOS") is True:
        return "ios"
    if data.get("LSRequiresIPhoneOS") is False and "mac" in platform:
        return "mac"
    sdk = str(data.get("DTSDKName") or "").lower()
    if sdk.startswith("macos"):
        return "mac"
    if sdk.startswith("iphone") or sdk.startswith("ipad"):
        return "ios"
    return ""


def _is_mac_device(value) -> bool:
    text = str(value or "")
    lower = text.lower()
    if any(token in text for token in ("iPhone", "iPad", "iPod")):
        return False
    return "Mac" in text or lower.startswith("mac") or "macos" in lower
