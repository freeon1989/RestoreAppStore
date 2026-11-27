
"""Обёртка над CLI ipatool-cpp (MIT). Пароль Apple ID в лог не пишется и на диск нами не сохраняется."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import paths

_TWO_FACTOR = re.compile(
    r"auth-?code|two[-\s]?factor|2fa|verification code|код подтверждения|код проверки",
    re.I,
)
_JSON_LINE = re.compile(r"(\{.*\}|\[.*\])", re.S)


class StoreError(Exception):
    def __init__(self, message: str, *, needs_2fa: bool = False, code: int = 0):
        super().__init__(message)
        self.needs_2fa = needs_2fa
        self.code = code


def parse_app_ref(text: str) -> dict:
    """Разбор поля поиска: ссылка App Store, числовой id, bundle id или строка."""
    raw = (text or "").strip()
    if not raw:
        return {"kind": "empty", "value": ""}
    m = re.search(r"apps\.apple\.com/[^/]+/app/[^/]*/id(\d+)", raw, re.I)
    if not m:
        m = re.search(r"apps\.apple\.com/.*/id(\d+)", raw, re.I)
    if not m:
        m = re.search(r"[?&]id=(\d+)", raw)
    if not m:
        m = re.search(r"/id(\d+)(?:\b|$)", raw)
    if m:
        return {"kind": "id", "value": m.group(1)}
    if re.fullmatch(r"\d{5,}", raw):
        return {"kind": "id", "value": raw}
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z0-9.-]+", raw) and "." in raw:
        return {"kind": "bundle", "value": raw}
    return {"kind": "term", "value": raw}


class Store:
    def __init__(self, exe: Path | None = None, passphrase: str | None = None):
        self.exe = Path(exe) if exe else paths.find_ipatool()
        self.passphrase = passphrase or ""

    def available(self) -> bool:
        return bool(self.exe and self.exe.is_file())

    def run(self, args: list[str], *, timeout: int = 180, stdin: str | None = None) -> dict | str:
        if not self.available():
            raise StoreError("Не найден ipatool-cpp. Положите его рядом с программой.")
        cmd = [str(self.exe), "--format", "json"]
        if self.passphrase:
            cmd += ["--keychain-passphrase", self.passphrase]
        cmd += args
        home = paths.tool_home()
        env = os.environ.copy()
        env["HOME"] = str(home)
        if sys.platform == "win32":
            env["USERPROFILE"] = str(home)
            drive, tail = os.path.splitdrive(str(home))
            env["HOMEDRIVE"] = drive or "C:"
            env["HOMEPATH"] = tail or "\\"
            env["LOCALAPPDATA"] = str(home / "AppData" / "Local")
            env["APPDATA"] = str(home / "AppData" / "Roaming")
        try:
            proc = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(home),
            )
        except subprocess.TimeoutExpired as exc:
            raise StoreError("ipatool-cpp не ответил вовремя") from exc
        except OSError as exc:
            raise StoreError(f"Не удалось запустить ipatool-cpp: {exc}") from exc
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        if proc.returncode != 0:
            message = _public_message(proc.stdout, proc.stderr) or f"ipatool-cpp завершился с кодом {proc.returncode}"
            raise StoreError(message, needs_2fa=_looks_like_2fa(out), code=proc.returncode)
        parsed = _parse_json(proc.stdout)
        return parsed if parsed is not None else (proc.stdout or "").strip()

    def login(self, email: str, password: str, auth_code: str | None = None) -> dict:
        args = ["auth", "login", "-e", email, "-p", password]
        if auth_code:
            args += ["--auth-code", auth_code]
        result = self.run(args, timeout=120)
        return result if isinstance(result, dict) else {"success": True, "email": email}

    def info(self) -> dict | None:
        try:
            result = self.run(["auth", "info"], timeout=30)
        except StoreError:
            return None
        return result if isinstance(result, dict) else None

    def revoke(self) -> None:
        try:
            self.run(["auth", "revoke"], timeout=30)
        except StoreError:
            pass

    def search(self, term: str, limit: int = 25) -> list[dict]:
        result = self.run(["search", term, "-l", str(limit)], timeout=90)
        return _as_apps(result)

    def list_purchases(self, *, entire: bool = False, since_year: int | None = None) -> list[dict]:
        args = ["list-purchases"]
        if entire:
            args.append("--all")
        elif since_year:
            args += ["--since-year", str(since_year)]
        result = self.run(args, timeout=600)
        return _as_apps(result)

    def list_versions(self, *, app_id: str | None = None, bundle: str | None = None,
                      buy: bool = False) -> list[dict]:
        args = ["list-versions"] + _id_flags(app_id, bundle)
        if buy:
            args.append("--purchase")
        result = self.run(args, timeout=180)
        return _as_versions(result)

    def purchase(self, *, app_id: str | None = None, bundle: str | None = None, force: bool = False) -> dict | str:
        args = ["purchase"] + _id_flags(app_id, bundle)
        if force:
            args.append("-f")
        return self.run(args, timeout=180)

    def download(self, dest: Path, *, app_id: str | None = None, bundle: str | None = None,
                 version_id: str | None = None, buy: bool = False) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        args = ["download"] + _id_flags(app_id, bundle) + ["-o", str(dest)]
        if version_id:
            args += ["--external-version-id", str(version_id)]
        if buy:
            args.append("--purchase")
        self.run(args, timeout=1800)
        if dest.is_file():
            return dest
        if dest.is_dir():
            ipas = sorted(dest.glob("*.ipa"), key=lambda p: p.stat().st_mtime, reverse=True)
            if ipas:
                return ipas[0]
        raise StoreError("Скачивание завершилось, но файл IPA не найден")


def _id_flags(app_id: str | None, bundle: str | None) -> list[str]:
    if app_id:
        return ["-i", str(app_id)]
    if bundle:
        return ["-b", str(bundle)]
    raise StoreError("Не указан идентификатор приложения")


def _parse_json(text: str):
    blob = (text or "").strip()
    if not blob:
        return None
    for candidate in (blob, blob.splitlines()[-1] if blob.splitlines() else ""):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    found = _JSON_LINE.search(blob)
    if found:
        try:
            return json.loads(found.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _as_apps(result) -> list[dict]:
    if isinstance(result, list):
        return [_normalize_app(item) for item in result if isinstance(item, dict)]
    if isinstance(result, dict):
        for key in ("apps", "results", "items", "purchases"):
            value = result.get(key)
            if isinstance(value, list):
                return [_normalize_app(item) for item in value if isinstance(item, dict)]
        if "id" in result or "bundleId" in result or "bundleID" in result or "name" in result:
            return [_normalize_app(result)]
    return []


def _as_versions(result) -> list[dict]:
    rows = []
    if isinstance(result, dict):
        for key in ("versions", "items", "results"):
            if isinstance(result.get(key), list):
                rows = result[key]
                break
        else:
            rows = [result] if "displayVersion" in result or "externalVersionId" in result else []
    elif isinstance(result, list):
        rows = result
    out = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        ver = str(item.get("displayVersion") or item.get("version") or item.get("bundleVersion") or "")
        ext = str(item.get("externalVersionId") or item.get("externalVersionID") or item.get("id") or "")
        date = str(item.get("releaseDate") or item.get("date") or "")
        ios = str(item.get("minimumOSVersion") or item.get("minOS") or "")
        sub = " · ".join(part for part in (date, f"iOS {ios}" if ios else "") if part)
        out.append({
            "value": ext or ver,
            "title": ver or ext or "версия",
            "sub": sub,
            "mine": bool(item.get("mine") or item.get("purchased")),
            "externalVersionId": ext,
            "displayVersion": ver,
        })
    return out


def _normalize_app(item: dict) -> dict:
    app_id = str(item.get("id") or item.get("trackId") or item.get("appId") or "")
    name = str(item.get("name") or item.get("trackName") or item.get("title") or "")
    bundle = str(item.get("bundleId") or item.get("bundleID") or item.get("bundle") or "")
    return {
        "id": app_id,
        "name": name,
        "bundle": bundle,
        "version": str(item.get("version") or item.get("displayVersion") or ""),
        "price": str(item.get("price") or item.get("formattedPrice") or ""),
        "date": str(item.get("purchaseDate") or item.get("releaseDate") or ""),
        "kind": str(item.get("kind") or item.get("genre") or ""),
        "genre": str(item.get("primaryGenreName") or item.get("genre") or item.get("kind") or ""),
        "icon": str(item.get("artworkUrl100") or item.get("icon") or ""),
        "raw": item,
    }


def _looks_like_2fa(text: str) -> bool:
    return bool(_TWO_FACTOR.search(text or ""))


def _public_message(stdout: str, stderr: str) -> str:
    text = "\n".join(part for part in (stderr, stdout) if part).strip()
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # не показываем дампы --debug и очевидные секреты
    useful = [line for line in lines if not re.search(r"password|token|passphrase|authorization:", line, re.I)]
    if not useful:
        return "Ошибка входа в App Store"
    return useful[-1][:400]
