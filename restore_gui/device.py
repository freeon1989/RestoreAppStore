"""iPhone (подключение, установщик) и файлы .ipa. Без интерфейса."""
import plistlib
import re
import shutil
import zipfile

import restore_apps as core


def own_pmd_folder():
    """Папка pymobiledevice3 — в папке программы (DATA_DIR\\pymobiledevice3), а не ~/.pymobiledevice3.

    pymobiledevice3 создаёт её при каждом подключении к iPhone и кладёт туда копию ключа сопряжения (основной
    хранит служба Apple). Своей настройки для этого у него нет: путь — переменная модуля, её и подменяем.
    """
    import pymobiledevice3.common
    pymobiledevice3.common._HOMEFOLDER = core.DATA_DIR / "pymobiledevice3"


def probe_device(timeout=8, pair=False):
    """Inspect USB devices; only an explicit connect action may request trust."""
    import asyncio

    def failure(state, message, error=None):
        return {"state": state, "message": message, "paired": False,
                "error": type(error).__name__ if error else ""}

    async def go():
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.usbmux import list_devices
        own_pmd_folder()
        devices = [d for d in await list_devices() if d.connection_type == "USB"]
        if not devices:
            return None
        ld = await create_using_usbmux(serial=devices[0].serial, connection_type="USB",
                                      autopair=pair, pair_timeout=timeout - 2 if pair else None)
        try:
            v = ld.all_values or {}
            paired = bool(getattr(ld, "paired", False))
            return {"ios": v.get("ProductVersion"), "model": ld.display_name or v.get("ProductType"),
                    "name": v.get("DeviceName"), "paired": paired,
                    "state": "ok" if paired else "trust",
                    "message": "" if paired else "Разблокируйте iPhone и нажмите «Подключить»"}
        finally:
            await ld.close()

    async def bounded():
        return await asyncio.wait_for(go(), timeout)

    try:
        return asyncio.run(bounded())
    except Exception as exc:
        name = type(exc).__name__
        if "Usbmux" in name or isinstance(exc, (ConnectionRefusedError, FileNotFoundError)):
            return failure("driver", "Нет связи со службой Apple. Откройте «Устройства Apple»", exc)
        if "Denied" in name:
            return failure("trust", "Доверие отклонено. Переподключите кабель и повторите", exc)
        if "Password" in name or "Locked" in name:
            return failure("trust", "Разблокируйте iPhone код-паролем и повторите", exc)
        if "Pair" in name or isinstance(exc, TimeoutError):
            return failure("trust", "Разблокируйте iPhone, нажмите «Доверять» и повторите", exc)
        return failure("error", "Не удалось подключить iPhone. Нажмите «Подключить» ещё раз", exc)


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:4]) or (0,)

def ipa_ok(path):
    try:
        with zipfile.ZipFile(path) as z:
            return any(n.startswith("Payload/") and n.endswith(".app/Info.plist") for n in z.namelist())
    except (OSError, zipfile.BadZipFile):
        return False


def ipa_info(ipa):
    """Info.plist приложения внутри IPA (CFBundleIdentifier, MinimumOSVersion, …) или {}."""
    try:
        with zipfile.ZipFile(ipa) as z:
            name = next(n for n in z.namelist()
                        if n.count("/") == 2 and n.startswith("Payload/") and n.endswith(".app/Info.plist"))
            return plistlib.loads(z.read(name))
    except (OSError, StopIteration, zipfile.BadZipFile, ValueError, plistlib.InvalidFileException):
        return {}


def installer_cmd(installer, action, ipa=None):
    """Команда установщика: action — "install" (ipa), "list" (установленные приложения) или "info" (сведения
    о телефоне). installer — ("builtin", [exe, "--pmd"]) | ("pymobiledevice3", путь) | ("ideviceinstaller", путь).
    None — у установщика нет такой команды."""
    kind, path = installer
    if kind in ("builtin", "pymobiledevice3"):
        base = list(path) if kind == "builtin" else [path]
        return base + {"install": ["apps", "install", str(ipa)], "list": ["apps", "list"],
                       "info": ["lockdown", "info"]}[action]
    if action == "install":
        return [path, "-i", str(ipa)]
    if action == "list":
        return [path, "-l"]
    info = shutil.which("ideviceinfo")  # у ideviceinstaller сведения о телефоне — отдельная программа
    return [info, "-k", "ProductVersion"] if info else None
