"""Понятные русские сообщения об ошибках установки. Сырой текст — только в журнал."""
from __future__ import annotations

import re

from .codesign import LEGACY_TEXT
from .ipa import CORRUPT_TEXT

# kind: legacy_signature, entitlements, signature, min_os, space, package_extract, other
_RULES: list[tuple[str, tuple[str, ...], str]] = [
    (
        "package_extract",
        (
            "packageextractionfailed",
            "could not extract archive",
            "failed to extract archive",
            "failed to extract the package",
        ),
        CORRUPT_TEXT,
    ),
    (
        "legacy_signature",
        (
            "0xe8008029", "e8008029",
            "code signature version is no longer supported",
            "the code signature version is no longer supported",
        ),
        LEGACY_TEXT,
    ),
    (
        "entitlements",
        (
            "0xe8008015", "e8008015",
            "a valid provisioning profile for this executable was not found",
            "could not verify executable",
            "entitlements",
        ),
        "Профиль или права приложения не подходят для этого устройства. Попробуйте другую версию.",
    ),
    (
        "signature",
        (
            "0xe800801c", "e800801c",
            "no valid code signature",
            "invalid signature",
            "failed to verify code signature",
        ),
        "Подпись приложения недействительна или повреждена. Скачайте версию заново или выберите другую.",
    ),
    (
        "min_os",
        (
            "minimumosversion",
            "requires a newer version of ios",
            "requires a newer version of ipados",
            "this app requires ios",
            "this app requires ipados",
            "inadequate features",
            "0xe800003a",  # sometimes used for OS mismatch; kept as fallback only with other tokens
        ),
        "Эта версия требует более новую iOS/iPadOS, чем на устройстве. Выберите более старую версию.",
    ),
    (
        "space",
        (
            "not enough disk space",
            "not enough storage",
            "there is not enough disk space",
            "insufficient space",
            "no space left",
            "0xe80000e8",
            "enospc",
        ),
        "На устройстве недостаточно места. Освободите память и попробуйте снова.",
    ),
]


class InstallError(Exception):
    def __init__(self, public: str, raw: str = "", kind: str = "other"):
        super().__init__(public)
        self.public = public
        self.raw = raw or ""
        self.kind = kind or "other"


def classify(text: str) -> str:
    blob = (text or "").lower()
    if not blob:
        return "other"
    # signature version must win over generic "failed to verify code signature"
    for kind, tokens, _msg in _RULES:
        if kind == "legacy_signature" and any(token in blob for token in tokens):
            return kind
    for kind, tokens, _msg in _RULES:
        if kind == "legacy_signature":
            continue
        if kind == "min_os":
            if "minimumosversion" in blob or "requires a newer version of io" in blob or "this app requires io" in blob:
                return kind
            continue
        if any(token in blob for token in tokens):
            return kind
    return "other"


def public_message(text: str) -> str:
    kind = classify(text)
    for item_kind, _tokens, message in _RULES:
        if item_kind == kind:
            return message
    return "Не удалось установить приложение на устройство. Подробности записаны в журнал."


def from_exception(exc: BaseException) -> InstallError:
    raw = str(exc or "").strip()
    kind = classify(raw)
    return InstallError(public_message(raw) if kind != "other" or _looks_raw(raw) else (raw[:300] or public_message(raw)), raw=raw, kind=kind)


def _looks_raw(text: str) -> bool:
    blob = (text or "").lower()
    if any(token in blob for token in ("0xe8", "applicationverificationfailed", "traceback", "coroutine", "exception")):
        return True
    return bool(re.search(r"/payload/|\.app\s*:|failed to verify", blob))
