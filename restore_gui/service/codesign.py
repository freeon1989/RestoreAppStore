"""Проверка подписи IPA: слишком старый CodeDirectory современная iOS уже не примет."""
from __future__ import annotations

import struct
import zipfile
from pathlib import Path

# Порог из требований: версия ниже 0x20400 (exec segment) — старый формат.
MIN_CD_VERSION = 0x20400
CSMAGIC_EMBEDDED_SIGNATURE = 0xFADE0CC0
CSMAGIC_CODEDIRECTORY = 0xFADE0C02
CSMAGIC_DETACHED_SIGNATURE = 0xFADE0CC1
CSMAGIC_EMBEDDED_DER_ENTITLEMENTS = 0xFADE7172
CSSLOT_CODEDIRECTORY = 0
CSSLOT_ALTERNATE = 0x1000
CSSLOT_DER_ENTITLEMENTS = 7
CS_HASHTYPE_SHA256 = 2
CS_HASHTYPE_SHA256_TRUNCATED = 3
CS_HASHTYPE_SHA384 = 4
MH_MAGIC = 0xFEEDFACE
MH_CIGAM = 0xCEFAEDFE
MH_MAGIC_64 = 0xFEEDFACF
MH_CIGAM_64 = 0xCFFAEDFE
FAT_MAGIC = 0xCAFEBABE
FAT_CIGAM = 0xBEBAFECA
FAT_MAGIC_64 = 0xCAFEBABF
FAT_CIGAM_64 = 0xBFBAFECA
LC_CODE_SIGNATURE = 0x1D
CPU_TYPE_ARM64 = 0x0100000C
CPU_TYPE_ARM = 0x0000000C

LEGACY_TEXT = (
    "Эта версия подписана старым форматом Apple, современная iOS/iPadOS её не принимает. "
    "Выберите более новую версию"
)


def inspect_ipa(path: Path | str) -> dict:
    """Разобрать подпись основного исполняемого файла в IPA.

    Возвращает словарь: ok, legacy, reason, cd_version, has_sha256, has_der, executable.
    Если подпись прочитать не удалось, legacy=False (не блокируем установку зря).
    """
    path = Path(path)
    result = {
        "ok": False,
        "legacy": False,
        "reason": "",
        "cd_version": 0,
        "has_sha256": False,
        "has_der": False,
        "executable": "",
    }
    if not path.is_file():
        result["reason"] = "файл не найден"
        return result
    try:
        blob, executable = _ipa_signature_blob(path)
    except Exception as exc:  # noqa: BLE001
        result["reason"] = f"не удалось прочитать подпись: {exc}"
        return result
    if not blob:
        result["reason"] = "в IPA нет подписи"
        # отсутствие подписи — тоже не установится, но это другой случай
        return result
    result["executable"] = executable
    parsed = parse_superblob(blob)
    result.update(parsed)
    result["ok"] = True
    if _is_legacy(parsed):
        result["legacy"] = True
        result["reason"] = LEGACY_TEXT
    return result


def parse_superblob(blob: bytes) -> dict:
    cds = []
    has_der = False
    if len(blob) < 12:
        return {"cd_version": 0, "has_sha256": False, "has_der": False, "directories": []}
    magic, length, count = struct.unpack(">III", blob[:12])
    if magic not in (CSMAGIC_EMBEDDED_SIGNATURE, CSMAGIC_DETACHED_SIGNATURE):
        # иногда передают один CodeDirectory
        if magic == CSMAGIC_CODEDIRECTORY:
            cds.append(_parse_cd(blob, 0))
        return _summary(cds, has_der)
    count = min(count, 64)
    for i in range(count):
        off = 12 + i * 8
        if off + 8 > len(blob):
            break
        slot, offset = struct.unpack(">II", blob[off:off + 8])
        if offset >= len(blob) or offset < 8:
            continue
        smagic = struct.unpack(">I", blob[offset:offset + 4])[0]
        if smagic == CSMAGIC_CODEDIRECTORY or slot == CSSLOT_CODEDIRECTORY or slot >= CSSLOT_ALTERNATE:
            if smagic == CSMAGIC_CODEDIRECTORY:
                cd = _parse_cd(blob, offset)
                if cd:
                    cds.append(cd)
        if smagic == CSMAGIC_EMBEDDED_DER_ENTITLEMENTS or slot == CSSLOT_DER_ENTITLEMENTS:
            has_der = True
    return _summary(cds, has_der)


def _parse_cd(blob: bytes, offset: int) -> dict | None:
    if offset + 40 > len(blob):
        return None
    magic, length, version, flags, hash_off, ident_off, n_special, n_code, code_limit = struct.unpack(
        ">IIIIIIIII", blob[offset:offset + 36]
    )
    if magic != CSMAGIC_CODEDIRECTORY:
        return None
    hash_size = blob[offset + 36]
    hash_type = blob[offset + 37]
    return {
        "version": version,
        "hash_type": hash_type,
        "hash_size": hash_size,
        "sha256": hash_type in (CS_HASHTYPE_SHA256, CS_HASHTYPE_SHA256_TRUNCATED, CS_HASHTYPE_SHA384),
        "length": length,
        "n_code": n_code,
    }


def _summary(cds: list[dict], has_der: bool) -> dict:
    version = max((item["version"] for item in cds), default=0)
    has_sha256 = any(item.get("sha256") for item in cds)
    return {
        "cd_version": version,
        "has_sha256": has_sha256,
        "has_der": has_der,
        "directories": cds,
    }


def _is_legacy(parsed: dict) -> bool:
    if not parsed.get("directories"):
        return False
    if not parsed.get("has_sha256"):
        return True
    if int(parsed.get("cd_version") or 0) < MIN_CD_VERSION:
        return True
    if not parsed.get("has_der"):
        return True
    return False


def _ipa_signature_blob(path: Path) -> tuple[bytes, str]:
    with zipfile.ZipFile(path) as zf:
        app_prefix = _app_prefix(zf)
        if not app_prefix:
            return b"", ""
        executable = _bundle_executable(zf, app_prefix) or _guess_executable(zf, app_prefix)
        if not executable:
            return b"", ""
        data = zf.read(executable)
        blob = macho_signature_blob(data)
        return blob, executable


def _app_prefix(zf: zipfile.ZipFile) -> str:
    for name in zf.namelist():
        parts = name.split("/")
        if len(parts) >= 2 and parts[0] == "Payload" and parts[1].endswith(".app"):
            return "/".join(parts[:2]) + "/"
    return ""


def _bundle_executable(zf: zipfile.ZipFile, prefix: str) -> str:
    info_name = prefix + "Info.plist"
    if info_name not in zf.namelist():
        return ""
    try:
        import plistlib
        info = plistlib.loads(zf.read(info_name))
    except Exception:
        return ""
    exe = str((info or {}).get("CFBundleExecutable") or "")
    if not exe:
        return ""
    return prefix + exe


def _guess_executable(zf: zipfile.ZipFile, prefix: str) -> str:
    # файл без расширения прямо в корне .app, не в подпапках
    candidates = []
    for name in zf.namelist():
        if not name.startswith(prefix) or name.endswith("/"):
            continue
        rest = name[len(prefix):]
        if "/" in rest or "." in rest.split("/")[-1]:
            continue
        candidates.append(name)
    return candidates[0] if len(candidates) == 1 else ""


def macho_signature_blob(data: bytes) -> bytes:
    if len(data) < 16:
        return b""
    magic = struct.unpack(">I", data[:4])[0]
    if magic in (FAT_MAGIC, FAT_CIGAM, FAT_MAGIC_64, FAT_CIGAM_64):
        slice_data = _best_fat_slice(data, magic)
        return _macho_blob(slice_data) if slice_data else b""
    return _macho_blob(data)


def _u32(data: bytes, offset: int, swapped: bool) -> int:
    if offset + 4 > len(data):
        return 0
    fmt = "<I" if swapped else ">I"
    return struct.unpack(fmt, data[offset:offset + 4])[0]


def _best_fat_slice(data: bytes, magic: int) -> bytes:
    swapped = magic in (FAT_CIGAM, FAT_CIGAM_64)
    wide = magic in (FAT_MAGIC_64, FAT_CIGAM_64)
    nfat = _u32(data, 4, swapped)
    nfat = min(nfat, 16)
    header = 8
    arm64 = None
    arm = None
    first = None
    for i in range(nfat):
        if wide:
            rec = header + i * 32
            if rec + 32 > len(data):
                break
            cputype = _u32(data, rec, swapped)
            offset = struct.unpack("<Q" if swapped else ">Q", data[rec + 8:rec + 16])[0]
            size = struct.unpack("<Q" if swapped else ">Q", data[rec + 16:rec + 24])[0]
        else:
            rec = header + i * 20
            if rec + 20 > len(data):
                break
            cputype = _u32(data, rec, swapped)
            offset = _u32(data, rec + 8, swapped)
            size = _u32(data, rec + 12, swapped)
        if offset + size > len(data):
            continue
        slice_data = data[offset:offset + size]
        if first is None:
            first = slice_data
        # cputype may be swapped independently; compare both endian interpretations
        if cputype in (CPU_TYPE_ARM64, struct.unpack("<I", struct.pack(">I", CPU_TYPE_ARM64))[0]):
            arm64 = slice_data
        elif cputype in (CPU_TYPE_ARM, struct.unpack("<I", struct.pack(">I", CPU_TYPE_ARM))[0]):
            arm = slice_data
    return arm64 or arm or first or b""


def _macho_blob(data: bytes) -> bytes:
    if len(data) < 32:
        return b""
    magic = struct.unpack(">I", data[:4])[0]
    if magic not in (MH_MAGIC, MH_CIGAM, MH_MAGIC_64, MH_CIGAM_64):
        return b""
    swapped = magic in (MH_CIGAM, MH_CIGAM_64)
    is64 = magic in (MH_MAGIC_64, MH_CIGAM_64)
    ncmds = _u32(data, 16, swapped)
    sizeofcmds = _u32(data, 20, swapped)
    off = 32 if is64 else 28
    end = min(len(data), off + sizeofcmds)
    ncmds = min(ncmds, 256)
    for _ in range(ncmds):
        if off + 8 > end:
            break
        cmd = _u32(data, off, swapped)
        cmdsize = _u32(data, off + 4, swapped)
        if cmdsize < 8:
            break
        if (cmd & 0xFFFFFFFF) == LC_CODE_SIGNATURE or (cmd & 0x7FFFFFFF) == LC_CODE_SIGNATURE:
            dataoff = _u32(data, off + 8, swapped)
            datasize = _u32(data, off + 12, swapped)
            if dataoff + datasize <= len(data):
                return data[dataoff:dataoff + datasize]
        off += cmdsize
    return b""
