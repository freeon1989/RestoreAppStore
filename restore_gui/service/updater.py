
"""Обновление RestoreAppStore из GitHub Releases.

Только HTTPS и только хосты GitHub. Файл сверяется с SHA-256 из рядом лежащего
ассета .sha256. Распаковка проверяет пути. Замену папки делает уже новая
копия с ключом --apply-update. Рядом остаётся резерв для кнопки «Вернуть».
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import restore_apps as core

REPO = core.REPO
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
PAGE_LATEST = f"https://github.com/{REPO}/releases/latest"
ASSET_ZIP = "RestoreAppStore-win-x64.zip"
ASSET_EXE = "RestoreAppStore-win-x64.exe"
ALLOWED_HOSTS = (
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
)
MAX_ZIP = 1024 * 1024 * 1024
MAX_UNPACKED = 3 * 1024 * 1024 * 1024
_VER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
UA = f"RestoreAppStore/{core.__version__} (+https://github.com/{REPO})"


class UpdateError(Exception):
    """Ошибка обновления с текстом для пользователя."""


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = _VER.match((value or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None


def is_newer(candidate: str, current: str | None = None) -> bool:
    left, right = parse_version(candidate), parse_version(current or core.__version__)
    return bool(left and right and left > right)


def backup_dir(current: str | None = None) -> Path | None:
    parent = Path(sys.executable).resolve().parent
    # onedir: .../RestoreAppStore/RestoreAppStore.exe → резерв рядом
    # onefile: exe лежит в выбранной папке
    name = f"RestoreAppStore.old-{_safe(current or core.__version__)}"
    for folder in (parent.parent, parent):
        candidate = folder / name
        if candidate.is_dir() or candidate.is_file():
            return candidate
    # ищем любой RestoreAppStore.old-*
    for folder in (parent.parent, parent):
        found = sorted(folder.glob("RestoreAppStore.old-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if found:
            return found[0]
    return None


def check_latest() -> dict:
    payload = _latest_payload()
    tag = str(payload.get("tag_name") or "").lstrip("v")
    notes = str(payload.get("body") or "").strip()
    html = str(payload.get("html_url") or PAGE_LATEST)
    assets = {str(item.get("name") or ""): str(item.get("browser_download_url") or "")
              for item in payload.get("assets") or [] if isinstance(item, dict)}
    return {
        "version": tag,
        "notes": notes,
        "html_url": html,
        "zip_url": assets.get(ASSET_ZIP, ""),
        "zip_sha_url": assets.get(ASSET_ZIP + ".sha256", ""),
        "exe_url": assets.get(ASSET_EXE, ""),
        "exe_sha_url": assets.get(ASSET_EXE + ".sha256", ""),
        "newer": is_newer(tag),
    }


def install_update(info: dict, log=lambda *_: None) -> None:
    """Скачать, проверить и запустить процедуру замены. Вызывает --apply-update и завершает текущий процесс."""
    if not getattr(sys, "frozen", False):
        raise UpdateError("Обновление из программы доступно в собранной Windows-версии")
    staging = Path(tempfile.mkdtemp(prefix="ras-update-"))
    try:
        target, kind = _install_target()
        if kind == "dir" and info.get("zip_url"):
            zip_path = staging / ASSET_ZIP
            _download(info["zip_url"], zip_path, log)
            expected = _read_sha(info.get("zip_sha_url") or "")
            actual = _sha256(zip_path)
            if expected and actual != expected:
                raise UpdateError("Сумма SHA-256 архива не совпала — файл повреждён или подменён")
            unpacked = staging / "unpacked"
            _safe_extract(zip_path, unpacked)
            new_root = _find_app_root(unpacked)
            log("Готово, заменяю программу…")
            _spawn_apply(new_root, target, kind)
        elif info.get("exe_url"):
            exe_path = staging / ASSET_EXE
            _download(info["exe_url"], exe_path, log)
            expected = _read_sha(info.get("exe_sha_url") or "")
            actual = _sha256(exe_path)
            if expected and actual != expected:
                raise UpdateError("Сумма SHA-256 файла не совпала — файл повреждён или подменён")
            log("Готово, заменяю программу…")
            _spawn_apply(exe_path, target, "file")
        else:
            raise UpdateError("В релизе нет файла обновления")
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def apply_update(argv: list[str]) -> int:
    """Вызывается из свежей копии: --apply-update <src> <dst> <kind> [parent-pid]."""
    if len(argv) < 3:
        print("usage: --apply-update SRC DST dir|file [PID]", file=sys.stderr)
        return 2
    src, dst, kind = Path(argv[0]), Path(argv[1]), argv[2]
    parent = int(argv[3]) if len(argv) > 3 and argv[3].isdigit() else None
    if parent:
        _wait_pid(parent, 60)
    if not src.exists():
        print("нет исходных файлов обновления", file=sys.stderr)
        return 1
    backup = dst.parent / f"RestoreAppStore.old-{_safe(core.__version__)}"
    try:
        if backup.exists():
            _rm(backup)
        if dst.exists():
            dst.rename(backup)
        if kind == "dir":
            shutil.copytree(src, dst)
            exe = _exe_in(dst)
        else:
            shutil.copy2(src, dst)
            exe = dst
        _launch(exe)
        return 0
    except Exception as exc:  # noqa: BLE001
        if backup.exists() and not dst.exists():
            try:
                backup.rename(dst)
            except OSError:
                pass
        print(f"не удалось применить обновление: {exc}", file=sys.stderr)
        return 1


def rollback() -> None:
    backup = backup_dir()
    if not backup or not backup.exists():
        raise UpdateError("Резервной копии нет")
    target, kind = _install_target()
    if not getattr(sys, "frozen", False):
        raise UpdateError("Откат доступен в собранной Windows-версии")
    staging = Path(tempfile.mkdtemp(prefix="ras-rollback-"))
    marker = staging / "src"
    if backup.is_dir():
        shutil.copytree(backup, marker)
        _spawn_apply(marker, target, "dir")
    else:
        shutil.copy2(backup, marker)
        _spawn_apply(marker, target, "file")


def _install_target() -> tuple[Path, str]:
    exe = Path(sys.executable).resolve()
    folder = exe.parent
    if (folder / "_internal").is_dir() or (folder / "RestoreAppStore.exe").is_file() and folder.name == "RestoreAppStore":
        return folder, "dir"
    return exe, "file"


def _spawn_apply(src: Path, dst: Path, kind: str) -> None:
    # Запускаем новую копию, чтобы она заменила текущую после нашего выхода.
    if kind == "dir":
        helper = _exe_in(src)
    else:
        helper = src
    args = [str(helper), "--apply-update", str(src), str(dst), kind, str(os.getpid())]
    subprocess.Popen(args, close_fds=True)
    # Даём новому процессу стартовать, затем выходим из текущего.
    time.sleep(0.4)
    os._exit(0)


def _exe_in(root: Path) -> Path:
    for candidate in (
        root / "RestoreAppStore.exe",
        root / "RestoreAppStore" / "RestoreAppStore.exe",
        root / "RestoreAppStore-win-x64.exe",
    ):
        if candidate.is_file():
            return candidate
    raise UpdateError("В архиве нет RestoreAppStore.exe")


def _find_app_root(unpacked: Path) -> Path:
    direct = unpacked / "RestoreAppStore" / "RestoreAppStore.exe"
    if direct.is_file():
        return unpacked / "RestoreAppStore"
    if (unpacked / "RestoreAppStore.exe").is_file():
        return unpacked
    found = list(unpacked.rglob("RestoreAppStore.exe"))
    if found:
        return found[0].parent
    raise UpdateError("В архиве нет RestoreAppStore.exe")


def _latest_payload() -> dict:
    try:
        raw = _http(API_LATEST, accept="application/vnd.github+json")
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict) and data.get("tag_name"):
            return data
    except (UpdateError, json.JSONDecodeError, OSError):
        pass
    # запасной путь: заголовок Location у /releases/latest
    loc = _head_location(PAGE_LATEST)
    tag = loc.rstrip("/").split("/")[-1] if loc else ""
    if not tag:
        raise UpdateError("Не удалось узнать последнюю версию на GitHub")
    return {"tag_name": tag, "body": "", "html_url": loc, "assets": [
        {"name": ASSET_ZIP, "browser_download_url": f"https://github.com/{REPO}/releases/latest/download/{ASSET_ZIP}"},
        {"name": ASSET_ZIP + ".sha256", "browser_download_url": f"https://github.com/{REPO}/releases/latest/download/{ASSET_ZIP}.sha256"},
        {"name": ASSET_EXE, "browser_download_url": f"https://github.com/{REPO}/releases/latest/download/{ASSET_EXE}"},
        {"name": ASSET_EXE + ".sha256", "browser_download_url": f"https://github.com/{REPO}/releases/latest/download/{ASSET_EXE}.sha256"},
    ]}


def _check_url(url: str) -> None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or host not in ALLOWED_HOSTS or parts.username or parts.port not in (None, 443):
        raise UpdateError("Адрес обновления вне GitHub — отказ")


def _http(url: str, accept: str = "*/*", hops: int = 6) -> bytes:
    for _ in range(hops):
        _check_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=45, context=ssl.create_default_context()) as resp:
                if resp.status in (301, 302, 303, 307, 308):
                    url = urljoin(url, resp.headers.get("Location") or "")
                    continue
                data = resp.read(MAX_ZIP + 1)
                if len(data) > MAX_ZIP:
                    raise UpdateError("Файл обновления слишком большой")
                return data
        except urllib.error.HTTPError as exc:
            if exc.status in (301, 302, 303, 307, 308):
                url = urljoin(url, exc.headers.get("Location") or "")
                continue
            raise UpdateError(f"GitHub вернул ошибку {exc.status}") from exc
        except OSError as exc:
            raise UpdateError(f"Не удалось связаться с GitHub: {exc}") from exc
    raise UpdateError("Слишком много перенаправлений")


def _head_location(url: str) -> str:
    _check_url(url)
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as resp:
            return resp.geturl() or url
    except OSError as exc:
        raise UpdateError(f"Не удалось открыть страницу релизов: {exc}") from exc


def _download(url: str, dest: Path, log) -> None:
    log(f"Скачиваю {dest.name}…")
    data = _http(url)
    dest.write_bytes(data)


def _read_sha(url: str) -> str:
    if not url:
        raise UpdateError("В релизе нет файла SHA-256 — обновление остановлено")
    text = _http(url).decode("utf-8", errors="replace")
    match = re.search(r"\b[a-fA-F0-9]{64}\b", text)
    if not match:
        raise UpdateError("Не удалось прочитать сумму SHA-256")
    return match.group(0).lower()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = info.filename
            if name.startswith("/") or ".." in Path(name).parts:
                raise UpdateError("В архиве небезопасный путь — отказ")
            total += info.file_size
            if total > MAX_UNPACKED:
                raise UpdateError("Распакованный архив слишком большой")
        zf.extractall(dest)


def _wait_pid(pid: int, seconds: int) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.3)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _launch(exe: Path) -> None:
    if sys.platform == "win32":
        subprocess.Popen([str(exe)], close_fds=True, cwd=str(exe.parent))
    else:
        subprocess.Popen([str(exe)], start_new_session=True, cwd=str(exe.parent))


def _rm(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _safe(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "_", value)[:32]
