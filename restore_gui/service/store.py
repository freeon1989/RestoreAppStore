
"""Обёртка над CLI ipatool-cpp (MIT). Пароль Apple ID в лог не пишется и на диск нами не сохраняется."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from . import paths

_TWO_FACTOR = re.compile(
    r"auth-?code|two[-\s]?factor|2fa|2fv|verification code|enter 2fa|trusted device|код подтверждения|код проверки",
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
        self._proc = None
        self._proc_lock = threading.Lock()

    def available(self) -> bool:
        return bool(self.exe and self.exe.is_file())

    def cancel(self) -> None:
        """Остановить текущий процесс ipatool-cpp, если он ещё идёт."""
        with self._proc_lock:
            proc = self._proc
        if proc is not None and proc.poll() is None:
            _kill_process(proc)

    def run(self, args: list[str], *, timeout: int = 180, stdin: str | None = None,
            stop_on_2fa: bool = False) -> dict | str:
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
        paths.write_app_log("ipatool: " + " ".join(public_command(cmd)))
        kwargs = dict(
            args=cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL if stdin is None else subprocess.PIPE,
            bufsize=0,
            env=env,
            cwd=str(home),
        )
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        try:
            proc = subprocess.Popen(**kwargs)
        except OSError as exc:
            paths.write_app_log(f"ipatool не запустился: {exc}")
            raise StoreError(f"Не удалось запустить ipatool-cpp: {exc}") from exc
        with self._proc_lock:
            self._proc = proc
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        flagged = threading.Event()

        def reader(stream, bucket):
            # бинарные куски: ipatool пишет «Enter 2FA code: » без перевода строки
            buf: list[str] = []
            try:
                while True:
                    chunk = stream.read(64)
                    if not chunk:
                        break
                    buf.append(chunk.decode("utf-8", errors="replace"))
                    text = "".join(buf)
                    if stop_on_2fa and _looks_like_2fa(text):
                        bucket.append(text)
                        buf.clear()
                        flagged.set()
                        _kill_process(proc)
                    elif "\n" in text:
                        bucket.append(text)
                        buf.clear()
            except OSError:
                pass
            if buf:
                bucket.append("".join(buf))

        threads = [
            threading.Thread(target=reader, args=(proc.stdout, stdout_parts), daemon=True),
            threading.Thread(target=reader, args=(proc.stderr, stderr_parts), daemon=True),
        ]
        for thread in threads:
            thread.start()
        timed_out = False
        try:
            if stdin is not None and proc.stdin:
                try:
                    payload = stdin if isinstance(stdin, (bytes, bytearray)) else str(stdin).encode("utf-8")
                    proc.stdin.write(payload)
                    proc.stdin.close()
                except OSError:
                    pass
            timed_out = False
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_process(proc)
                proc.wait(timeout=5)
                timed_out = True
                paths.write_app_log(f"ipatool не ответил за {timeout} с, процесс остановлен")
        finally:
            for thread in threads:
                thread.join(timeout=2)
            for stream in (proc.stdout, proc.stderr, proc.stdin):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
            with self._proc_lock:
                if self._proc is proc:
                    self._proc = None
        stdout = "".join(stdout_parts)
        stderr = "".join(stderr_parts)
        code = proc.returncode if proc.returncode is not None else -1
        public_err = redact_text(stderr)[:800].replace("\n", " | ")
        paths.write_app_log(f"ipatool код={code}" + (f" stderr: {public_err}" if public_err else ""))
        combined = stdout + (("\n" + stderr) if stderr else "")
        if stop_on_2fa and (flagged.is_set() or _looks_like_2fa(combined)):
            raise StoreError(
                "Нужен код подтверждения, который Apple прислала на ваши устройства.",
                needs_2fa=True,
                code=code,
            )
        if timed_out:
            raise StoreError(
                f"Операция не завершилась за {timeout} с. Проверьте сеть и откройте журнал, если ошибка повторится."
            )
        if code != 0:
            message = _public_message(stdout, stderr) or f"ipatool-cpp завершился с кодом {code}"
            raise StoreError(message, needs_2fa=_looks_like_2fa(combined), code=code)
        parsed = _parse_json(stdout)
        return parsed if parsed is not None else (stdout or "").strip()

    def login(self, email: str, password: str, auth_code: str | None = None) -> dict:
        args = ["auth", "login", "-e", email, "-p", password]
        if auth_code:
            args += ["--auth-code", auth_code]
        result = self.run(args, timeout=60, stop_on_2fa=not auth_code)
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




_SECRET_FLAGS = {
    "-p", "--password", "-e", "--email", "-a", "--auth-code", "--keychain-passphrase",
}


def public_command(cmd: list[str]) -> list[str]:
    """Аргументы для журнала: пароль, код и адрес заменены на ***."""
    out: list[str] = []
    hide = False
    for item in cmd:
        if hide:
            out.append("***")
            hide = False
            continue
        name, _, value = item.partition("=")
        flag = name.lower()
        if flag in _SECRET_FLAGS or flag.split("/")[-1] in {s.lstrip("-") for s in _SECRET_FLAGS}:
            if value:
                out.append(f"{name}=***")
            else:
                out.append(item)
                hide = True
            continue
        # не пишем путь с домашней папкой пользователя
        out.append(Path(item).name if (item.endswith(".exe") and "\\" in item or "/" in item and item.endswith(".exe")) else item)
    return out


def redact_text(text: str) -> str:
    """Убрать из текста пароли, коды и похожие секреты перед записью в журнал."""
    cleaned = text or ""
    cleaned = re.sub(r"(?i)(password|passphrase|auth-?code|token|authorization)\s*[=:]\s*\S+", r"\1=***", cleaned)
    cleaned = re.sub(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "***@***", cleaned)
    return cleaned


def _kill_process(proc) -> None:
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    except OSError:
        pass


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
