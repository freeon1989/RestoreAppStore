"""Подключение iPhone, iPad и iPod touch и установка IPA.

Основной путь — публичный API pymobiledevice3, если пакет установлен.
Это сторонний компонент под GPL-3.0: см. THIRD_PARTY_NOTICES.md.
Если пакета нет, пробуем ideviceinstaller из PATH (libimobiledevice, LGPL).

В pymobiledevice3 11 list_devices и create_using_usbmux стали async:
синхронный вызов даёт TypeError («coroutine is not iterable»), и устройство
кажется «невидимым», хотя служба Apple на 127.0.0.1:27015 работает.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import traceback
from pathlib import Path

from restore_gui.service import paths

TRUST_TEXT = "Разблокируйте iPhone или iPad и нажмите «Доверять»"
NONE_TEXT = "Подключите iPhone или iPad кабелем"
NOT_FOUND_TEXT = "iPhone или iPad не найден. Подключите кабель."
MUX_DOWN_TEXT = (
    "Служба «Устройства Apple» не отвечает на 127.0.0.1:27015. "
    "Откройте или переустановите приложение «Устройства Apple» из Microsoft Store."
)


def mask_udid(udid: str) -> str:
    """Частично скрыть UDID для журнала: видны начало и конец."""
    text = (udid or "").strip()
    if len(text) <= 8:
        return text or "—"
    return text[:8] + "…" + text[-4:]


def kind_from_identity(product_type: str = "", device_class: str = "") -> str:
    """Человекочитаемый тип: iPhone, iPad, iPod или «устройство»."""
    blob = f"{device_class} {product_type}".lower()
    if "ipad" in blob:
        return "iPad"
    if "ipod" in blob:
        return "iPod"
    if "iphone" in blob:
        return "iPhone"
    return "устройство"


def is_trust_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    name = type(exc).__name__.lower()
    tokens = (
        "trust", "pair", "password", "unlock", "not paired", "not trusted",
        "passcode", "pairingdialog", "userdenied", "passwordprotected",
    )
    return any(token in message or token in name for token in tokens)


def pair_record_dirs() -> list[Path]:
    """Каталоги с pair record: iTunes/ProgramData, пакет Apple Devices, папка программы."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            key = str(path.resolve()) if path.exists() else str(path)
        except OSError:
            key = str(path)
        if key not in seen:
            seen.add(key)
            found.append(path)

    programdata = os.environ.get("ALLUSERSPROFILE") or os.environ.get("PROGRAMDATA") or ""
    if programdata:
        add(Path(programdata) / "Apple" / "Lockdown")
    local = os.environ.get("LOCALAPPDATA") or ""
    if local:
        packages = Path(local) / "Packages"
        try:
            for pkg in packages.glob("AppleInc.AppleDevices*"):
                for rel in (
                    Path("LocalState") / "Apple" / "Lockdown",
                    Path("LocalState") / "Lockdown",
                    Path("LocalCache") / "Apple" / "Lockdown",
                    Path("AC") / "Apple" / "Lockdown",
                ):
                    cand = pkg / rel
                    if cand.is_dir():
                        add(cand)
        except OSError:
            pass
    add(our_pair_dir())
    return found


def our_pair_dir() -> Path:
    return paths.logs_dir() / "Lockdown"


def status(*, autopair: bool = False, pair_timeout: float = 45) -> dict:
    """state: none | trust | ok; text — строка для интерфейса."""
    try:
        return _status_pmd(autopair=autopair, pair_timeout=pair_timeout)
    except ImportError as exc:
        paths.write_app_log(f"устройство: pymobiledevice3 не импортировался: {exc}")
    except Exception as exc:  # noqa: BLE001 — любое состояние устройства показываем текстом
        paths.write_app_log(f"устройство: {type(exc).__name__}: {exc}")
        if is_trust_error(exc):
            return {"state": "trust", "text": TRUST_TEXT, "udid": "", "apps": []}
        if "usbmux" in str(exc).lower() or "27015" in str(exc) or type(exc).__name__ == "ConnectionFailedToUsbmuxdError":
            return {"state": "none", "text": MUX_DOWN_TEXT, "udid": "", "apps": []}
        return {"state": "none", "text": str(exc)[:240] or NONE_TEXT, "udid": "", "apps": []}
    if shutil.which("idevice_id") or shutil.which("ideviceinstaller"):
        return _status_libimobile()
    return {"state": "none", "text": NONE_TEXT, "udid": "", "apps": []}


def install_ipa(path: Path) -> None:
    path = Path(path)
    if not path.is_file():
        raise RuntimeError(f"Файл не найден: {path}")
    try:
        _run_async(_install_pmd_async(path))
        return
    except ImportError:
        pass
    exe = shutil.which("ideviceinstaller")
    if not exe:
        raise RuntimeError("Нет средства установки на устройство (pymobiledevice3 или ideviceinstaller)")
    proc = subprocess.run([exe, "-i", str(path)], capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "ideviceinstaller не смог установить IPA").strip()[:400])


def write_diagnostics() -> int:
    """Диагностика usbmux/lockdown в app.log (и на stdout). Код 0, если устройство уже сопряжено."""
    lines: list[str] = []

    def note(text: str) -> None:
        lines.append(text)
        paths.write_app_log("diag: " + text)
        print(text, flush=True)

    note(f"RestoreAppStore диагностика устройства, Python {sys.version.split()[0]}, {sys.platform}")
    try:
        import pymobiledevice3
        ver = getattr(pymobiledevice3, "__version__", "") or ""
        if not ver:
            try:
                from importlib.metadata import version as pkg_version
                ver = pkg_version("pymobiledevice3")
            except Exception:
                ver = "?"
        note(f"pymobiledevice3 {ver}")
    except Exception as exc:  # noqa: BLE001
        note(f"pymobiledevice3 не импортировался: {exc}")
        return 2

    address = "127.0.0.1:27015"
    try:
        from pymobiledevice3.osu.os_utils import get_os_utils
        raw, _family = get_os_utils().usbmux_address
        if isinstance(raw, tuple):
            address = f"{raw[0]}:{raw[1]}"
        else:
            address = str(raw)
    except Exception as exc:  # noqa: BLE001
        note(f"адрес usbmux по умолчанию не получен: {exc}")
    note(f"usbmux адрес {address}")

    host, _, port_s = address.partition(":")
    if port_s.isdigit():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            sock.connect((host, int(port_s)))
            note(f"TCP {address}: соединение установлено")
        except OSError as exc:
            note(f"TCP {address}: нет соединения ({exc})")
        finally:
            sock.close()

    for folder in pair_record_dirs():
        exists = folder.is_dir()
        writable = os.access(folder, os.W_OK) if exists else False
        if not exists:
            try:
                folder.mkdir(parents=True, exist_ok=True)
                exists = folder.is_dir()
                writable = os.access(folder, os.W_OK) if exists else False
                created = True
            except OSError:
                created = False
        else:
            created = False
        names = []
        if exists:
            try:
                names = [p.name for p in folder.glob("*.plist")]
            except OSError as exc:
                note(f"пара: {folder} — не прочитать ({exc})")
                continue
        masked = [mask_udid(Path(name).stem) + ".plist" for name in names]
        access = "запись есть" if writable else ("есть, без записи" if exists else "нет")
        extra = ", создана сейчас" if created else ""
        note(f"пара: {folder} — {access}{extra}, записей {len(names)}" + (f": {', '.join(masked)}" if masked else ""))

    try:
        devices = _run_async(_list_devices())
        if not devices:
            note("usbmux: устройств нет")
        for dev in devices:
            serial = getattr(dev, "serial", "") or ""
            ctype = getattr(dev, "connection_type", "") or ""
            devid = getattr(dev, "devid", "")
            note(f"usbmux: id={devid} type={ctype} udid={mask_udid(serial)}")
    except Exception as exc:  # noqa: BLE001
        note(f"list_devices: {type(exc).__name__}: {exc}")
        if type(exc).__name__ != "ConnectionFailedToUsbmuxdError":
            note(traceback.format_exc(limit=6))
        return 3

    try:
        info = _status_pmd(autopair=False, pair_timeout=5)
        note(f"lockdown: state={info.get('state')} text={info.get('text')} udid={mask_udid(info.get('udid') or '')}")
        return 0 if info.get("state") == "ok" else 1
    except Exception as exc:  # noqa: BLE001
        note(f"lockdown: {type(exc).__name__}: {exc}")
        note(traceback.format_exc(limit=8))
        return 4


def _run_async(coro):
    """Запустить корутину pymobiledevice3 из обычного потока."""
    from pymobiledevice3.utils import run_in_loop
    return run_in_loop(coro)


async def _list_devices():
    from pymobiledevice3.usbmux import list_devices
    return list(await list_devices())


def _status_pmd(*, autopair: bool, pair_timeout: float) -> dict:
    return _run_async(_status_pmd_async(autopair=autopair, pair_timeout=pair_timeout))


async def _status_pmd_async(*, autopair: bool, pair_timeout: float) -> dict:
    from pymobiledevice3.exceptions import ConnectionFailedToUsbmuxdError
    from pymobiledevice3.lockdown import create_using_usbmux

    try:
        devices = await _list_devices()
    except ConnectionFailedToUsbmuxdError:
        return {"state": "none", "text": MUX_DOWN_TEXT, "udid": "", "apps": []}

    if not devices:
        paths.write_app_log("устройство: usbmux ответил, список пуст")
        return {"state": "none", "text": NOT_FOUND_TEXT, "udid": "", "apps": []}

    summaries = []
    for dev in devices:
        serial = getattr(dev, "serial", "") or str(dev)
        ctype = getattr(dev, "connection_type", "") or ""
        summaries.append(f"{ctype or 'USB'} {mask_udid(serial)}")
    paths.write_app_log("устройство: usbmux " + ", ".join(summaries))

    usb = [dev for dev in devices if str(getattr(dev, "connection_type", "")).upper() == "USB"]
    dev = (usb or devices)[0]
    udid = getattr(dev, "serial", None) or str(dev)
    cache = our_pair_dir()
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache = None

    try:
        client = await create_using_usbmux(
            serial=udid,
            autopair=autopair,
            pair_timeout=pair_timeout if autopair else 0,
            pairing_records_cache_folder=cache,
        )
    except Exception as exc:
        if is_trust_error(exc):
            paths.write_app_log(f"устройство: нет пары ({type(exc).__name__}: {exc}), udid={mask_udid(udid)}")
            return {"state": "trust", "text": TRUST_TEXT, "udid": udid, "apps": []}
        raise

    try:
        product = str(getattr(client, "product_type", "") or "")
        device_class = ""
        try:
            device_class = str((client.all_values or {}).get("DeviceClass") or "")
        except Exception:
            pass
        kind = kind_from_identity(product, device_class)
        name = client.display_name or kind
        ios = client.product_version or ""
        os_name = "iPadOS" if kind == "iPad" else "iOS"
        text = f"{name}" + (f" · {os_name} {ios}" if ios else "")
        apps = await _installed_pmd(client)
        paths.write_app_log(f"устройство: ок {kind} udid={mask_udid(udid)} {text}")
        return {"state": "ok", "text": text, "udid": udid, "apps": apps, "kind": kind}
    finally:
        try:
            await client.close()
        except Exception:
            pass


async def _installed_pmd(client) -> list[dict]:
    try:
        from pymobiledevice3.services.installation_proxy import InstallationProxyService
        async with InstallationProxyService(lockdown=client) as svc:
            items = await svc.get_apps(application_type="User") or {}
    except Exception as exc:  # noqa: BLE001 — список приложений не обязателен для «устройство видно»
        paths.write_app_log(f"устройство: список приложений недоступен ({type(exc).__name__}: {exc})")
        return []
    out = []
    if isinstance(items, dict):
        values = items.values()
    else:
        values = items
    for item in values:
        if not isinstance(item, dict):
            continue
        out.append({
            "id": str(item.get("CFBundleIdentifier") or ""),
            "name": str(item.get("CFBundleDisplayName") or item.get("CFBundleName") or ""),
            "version": str(item.get("CFBundleShortVersionString") or item.get("CFBundleVersion") or ""),
        })
    return out


async def _install_pmd_async(path: Path) -> None:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.installation_proxy import InstallationProxyService

    cache = our_pair_dir()
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache = None
    client = await create_using_usbmux(autopair=True, pair_timeout=45, pairing_records_cache_folder=cache)
    try:
        async with InstallationProxyService(lockdown=client) as svc:
            await svc.install_from_local(str(path))
    finally:
        try:
            await client.close()
        except Exception:
            pass


def _status_libimobile() -> dict:
    exe = shutil.which("idevice_id")
    if not exe:
        return {"state": "none", "text": NONE_TEXT, "udid": "", "apps": []}
    proc = subprocess.run([exe, "-l"], capture_output=True, text=True, timeout=15)
    udids = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    if not udids:
        return {"state": "none", "text": NOT_FOUND_TEXT, "udid": "", "apps": []}
    return {"state": "ok", "text": "Устройство подключено", "udid": udids[0], "apps": []}
