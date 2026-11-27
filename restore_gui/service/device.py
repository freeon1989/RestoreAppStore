
"""Подключение iPhone и установка IPA.

Основной путь — публичный API pymobiledevice3, если пакет установлен.
Это сторонний компонент под GPL-3.0: см. THIRD_PARTY_NOTICES.md.
Если пакета нет, пробуем ideviceinstaller из PATH (libimobiledevice, LGPL).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def status() -> dict:
    """state: none | trust | ok; text — строка для интерфейса."""
    try:
        return _status_pmd()
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001 — любое состояние устройства показываем текстом
        message = str(exc).lower()
        if "trust" in message or "pair" in message or "password" in message or "unlock" in message:
            return {"state": "trust", "text": "Разблокируйте iPhone и нажмите «Доверять»", "udid": "", "apps": []}
        return {"state": "none", "text": str(exc)[:200], "udid": "", "apps": []}
    if shutil.which("idevice_id") or shutil.which("ideviceinstaller"):
        return _status_libimobile()
    return {"state": "none", "text": "Подключите iPhone кабелем", "udid": "", "apps": []}


def install_ipa(path: Path) -> None:
    path = Path(path)
    if not path.is_file():
        raise RuntimeError(f"Файл не найден: {path}")
    try:
        _install_pmd(path)
        return
    except ImportError:
        pass
    exe = shutil.which("ideviceinstaller")
    if not exe:
        raise RuntimeError("Нет средства установки на iPhone (pymobiledevice3 или ideviceinstaller)")
    proc = subprocess.run([exe, "-i", str(path)], capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "ideviceinstaller не смог установить IPA").strip()[:400])


def _status_pmd() -> dict:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.usbmux import list_devices

    devices = list(list_devices())
    if not devices:
        return {"state": "none", "text": "iPhone не найден. Подключите кабель.", "udid": "", "apps": []}
    dev = devices[0]
    udid = getattr(dev, "serial", None) or str(dev)
    client = create_using_usbmux(serial=udid)
    name = client.display_name or client.product_type or "iPhone"
    ios = client.product_version or ""
    text = f"{name}" + (f" · iOS {ios}" if ios else "")
    apps = _installed_pmd(client)
    return {"state": "ok", "text": text, "udid": udid, "apps": apps}


def _installed_pmd(client) -> list[dict]:
    try:
        from pymobiledevice3.services.installation_proxy import InstallationProxyService
        with InstallationProxyService(lockdown=client) as svc:
            items = svc.get_apps(application_type="User") or {}
    except Exception:
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


def _install_pmd(path: Path) -> None:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.installation_proxy import InstallationProxyService

    client = create_using_usbmux()
    with InstallationProxyService(lockdown=client) as svc:
        svc.install_from_local(str(path))


def _status_libimobile() -> dict:
    exe = shutil.which("idevice_id")
    if not exe:
        return {"state": "none", "text": "Подключите iPhone кабелем", "udid": "", "apps": []}
    proc = subprocess.run([exe, "-l"], capture_output=True, text=True, timeout=15)
    udids = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    if not udids:
        return {"state": "none", "text": "iPhone не найден. Подключите кабель.", "udid": "", "apps": []}
    return {"state": "ok", "text": "iPhone подключён", "udid": udids[0], "apps": []}
