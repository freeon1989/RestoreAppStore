
"""Пароль шифрования сессии ipatool-cpp: Windows Credential Manager или DPAPI, без пароля Apple ID."""
from __future__ import annotations

import os
import secrets as stdlib_secrets
import sys
from pathlib import Path

from . import paths

TARGET = "RestoreAppStore/ipatool-passphrase"
FALLBACK = "keychain.dpapi"


class SecretError(Exception):
    """Не удалось прочитать или записать секрет."""


def _fallback_file() -> Path:
    return paths.data_dir() / FALLBACK


def load_passphrase() -> str:
    raw = _read_windows() if sys.platform == "win32" else None
    if not raw:
        raw = _read_fallback()
    if not raw:
        raw = stdlib_secrets.token_urlsafe(32)
        store_passphrase(raw)
    return raw


def store_passphrase(value: str) -> None:
    data = value.encode("utf-8")
    if sys.platform == "win32":
        try:
            _write_windows(data)
            return
        except OSError:
            pass
    _write_fallback(data)


def _write_fallback(data: bytes) -> None:
    blob = _protect(data)
    path = _fallback_file()
    path.write_bytes(blob)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _read_fallback() -> str | None:
    path = _fallback_file()
    if not path.is_file():
        return None
    try:
        return _unprotect(path.read_bytes()).decode("utf-8")
    except (OSError, ValueError, SecretError):
        return None


def _protect(data: bytes) -> bytes:
    if sys.platform == "win32":
        return _dpapi_protect(data)
    return data


def _unprotect(blob: bytes) -> bytes:
    if sys.platform == "win32":
        return _dpapi_unprotect(blob)
    return blob


def _dpapi_protect(data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(data)
    inp = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    out = DATA_BLOB()
    if not crypt32.CryptProtectData(ctypes.byref(inp), "RestoreAppStore", None, None, None, 0, ctypes.byref(out)):
        raise SecretError("CryptProtectData failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


def _dpapi_unprotect(blob: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(blob)
    inp = DATA_BLOB(len(blob), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    out = DATA_BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)):
        raise SecretError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


def _write_windows(data: bytes) -> None:
    import ctypes
    from ctypes import wintypes

    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    blob = ctypes.create_string_buffer(data)
    cred = CREDENTIAL()
    cred.Type = CRED_TYPE_GENERIC
    cred.TargetName = TARGET
    cred.CredentialBlobSize = len(data)
    cred.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_byte))
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE
    cred.UserName = "RestoreAppStore"
    if not ctypes.windll.advapi32.CredWriteW(ctypes.byref(cred), 0):
        raise OSError("CredWriteW failed")


def _read_windows() -> str | None:
    import ctypes
    from ctypes import wintypes

    CRED_TYPE_GENERIC = 1

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    ptr = ctypes.c_void_p()
    advapi32 = ctypes.windll.advapi32
    if not advapi32.CredReadW(TARGET, CRED_TYPE_GENERIC, 0, ctypes.byref(ptr)):
        return None
    try:
        cred = ctypes.cast(ptr, ctypes.POINTER(CREDENTIAL)).contents
        raw = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
        return raw.decode("utf-8")
    finally:
        advapi32.CredFree(ptr)
