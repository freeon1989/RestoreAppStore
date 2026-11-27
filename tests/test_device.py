import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))
import sandbox  # noqa: E402
from restore_gui.service import device  # noqa: E402
from restore_gui.service import paths  # noqa: E402


class MaskAndKindTests(unittest.TestCase):
    def test_mask_udid(self):
        self.assertEqual(device.mask_udid("00008120-0011223344556677"), "00008120…6677")
        self.assertEqual(device.mask_udid("short"), "short")

    def test_kind(self):
        self.assertEqual(device.kind_from_identity("iPad13,16", "iPad"), "iPad")
        self.assertEqual(device.kind_from_identity("iPhone15,2", "iPhone"), "iPhone")
        self.assertEqual(device.kind_from_identity("iPod9,1", ""), "iPod")
        self.assertEqual(device.kind_from_identity("Watch6,1", "Watch"), "устройство")

    def test_trust_error(self):
        self.assertTrue(device.is_trust_error(RuntimeError("Please unlock the device and tap Trust")))
        self.assertTrue(device.is_trust_error(RuntimeError("NotPairedError: device should be paired first")))
        self.assertFalse(device.is_trust_error(RuntimeError("connection refused")))


class FakeMuxDevice:
    def __init__(self, serial="00008120-0011223344556677", connection_type="USB", devid=3):
        self.serial = serial
        self.connection_type = connection_type
        self.devid = devid


class AsyncApiTests(unittest.TestCase):
    def test_empty_list_is_none_not_typeerror(self):
        async def fake_list():
            return []

        with mock.patch.object(device, "_list_devices", fake_list):
            info = device._status_pmd(autopair=False, pair_timeout=1)
        self.assertEqual(info["state"], "none")
        self.assertIn("iPad", info["text"])

    def test_ipad_unpaired_is_trust(self):
        async def fake_list():
            return [FakeMuxDevice()]

        async def fake_create(**_kwargs):
            raise RuntimeError("Device is not paired. Unlock and trust this computer.")

        with mock.patch.object(device, "_list_devices", fake_list), mock.patch(
            "pymobiledevice3.lockdown.create_using_usbmux", fake_create
        ):
            info = device._status_pmd(autopair=True, pair_timeout=1)
        self.assertEqual(info["state"], "trust")
        self.assertIn("Доверять", info["text"])
        self.assertEqual(info["udid"], "00008120-0011223344556677")

    def test_ok_ipad_label(self):
        class Client:
            product_type = "iPad13,16"
            all_values = {"DeviceClass": "iPad"}
            display_name = "iPad Про"
            product_version = "17.6"
            async def close(self):
                return None

        async def fake_list():
            return [FakeMuxDevice()]

        async def fake_create(**_kwargs):
            return Client()

        async def no_apps(_client):
            return []

        with mock.patch.object(device, "_list_devices", fake_list), mock.patch(
            "pymobiledevice3.lockdown.create_using_usbmux", fake_create
        ), mock.patch.object(device, "_installed_pmd", no_apps):
            info = device._status_pmd(autopair=False, pair_timeout=1)
        self.assertEqual(info["state"], "ok")
        self.assertEqual(info["kind"], "iPad")
        self.assertIn("iPadOS 17.6", info["text"])


class DiagTests(unittest.TestCase):
    def test_write_diagnostics_logs(self):
        code = device.write_diagnostics()
        self.assertIn(code, (0, 1, 2, 3, 4))
        text = paths.app_log_path().read_text(encoding="utf-8")
        self.assertIn("diag:", text)
        self.assertIn("pymobiledevice3", text)
        self.assertNotRegex(text, r"00008120-0011223344556677")


class LogDedupeTests(unittest.TestCase):
    def test_on_device_logs_only_on_change(self):
        from PySide6.QtWidgets import QApplication
        from restore_gui.backend import Backend

        app = QApplication.instance() or QApplication(["test"])
        backend = Backend(background=False)
        backend._log_lines.clear()
        backend._last_device_log = None
        result = {"state": "none", "text": "iPhone или iPad не найден. Подключите кабель.", "udid": "", "apps": []}
        backend._on_device(result, None)
        first = list(backend._log_lines)
        backend._on_device(result, None)
        self.assertEqual(backend._log_lines, first)
        backend._on_device({"state": "trust", "text": device.TRUST_TEXT, "udid": "ABCD1234EF", "apps": []}, None)
        self.assertGreater(len(backend._log_lines), len(first))
        self.assertIn("Доверять", backend._log_lines[-1])
