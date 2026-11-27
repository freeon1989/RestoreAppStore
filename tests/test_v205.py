import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))
import sandbox  # noqa: E402

from restore_gui.service import accounts, codesign, itunes, progress, regions  # noqa: E402
from restore_gui.service.install_errors import classify, public_message, from_exception  # noqa: E402
from restore_gui.service.codesign import LEGACY_TEXT, MIN_CD_VERSION, parse_superblob  # noqa: E402


class RegionTests(unittest.TestCase):
    def test_parse_letter_and_numeric(self):
        self.assertEqual(regions.parse_storefront("US"), "us")
        self.assertEqual(regions.parse_storefront("143441-1,29"), "us")
        self.assertEqual(regions.parse_storefront("143469"), "ru")
        self.assertEqual(regions.parse_storefront(""), "")

    def test_unavailable_message(self):
        text = regions.unavailable_message(["us"])
        self.assertIn("App Store США", text)
        self.assertIn("войдите в Apple ID этой страны", text)

    def test_is_region_error(self):
        self.assertTrue(regions.is_region_error(
            "app is not available for download in your region/storefront (license was granted but download was blocked)"
        ))
        self.assertFalse(regions.is_region_error("network timeout"))


class AccountStoreTests(unittest.TestCase):
    def test_save_strips_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with mock.patch("restore_gui.service.accounts.paths.data_dir", return_value=folder):
                accounts.save({
                    "current": "a1",
                    "accounts": [{"id": "a1", "email": "user@example.com", "storefront": "us", "password": "secret"}],
                })
                raw = json.loads((folder / "accounts.json").read_text(encoding="utf-8"))
                self.assertEqual(raw["accounts"][0]["email"], "user@example.com")
                self.assertNotIn("password", raw["accounts"][0])
                loaded = accounts.load()
                self.assertEqual(loaded["accounts"][0]["storefront"], "us")
                self.assertNotIn("password", loaded["accounts"][0])


class ProgressParseTests(unittest.TestCase):
    def test_ipatool_line(self):
        line = "Downloading:  45% (12.3 MB/40.0 MB, 3.1 MB/s)"
        hit = progress.parse_download_progress(line)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["pct"], 45)
        self.assertAlmostEqual(hit["done"], 12.3 * 1000 ** 2, delta=1000)
        self.assertAlmostEqual(hit["total"], 40 * 1000 ** 2, delta=1000)
        self.assertAlmostEqual(hit["speed"], 3.1 * 1000 ** 2, delta=1000)
        text = progress.format_download(hit["pct"], hit["done"], hit["total"], hit["speed"])
        self.assertIn("%", text)
        self.assertIn("МБ", text)
        self.assertIn("/с", text)

    def test_cr_updates_take_last(self):
        blob = "Downloading:  10% (1.0 MB/10.0 MB, 1.0 MB/s)\rDownloading:  80% (8.0 MB/10.0 MB, 2.0 MB/s)"
        hit = progress.parse_download_progress(blob)
        self.assertEqual(hit["pct"], 80)

    def test_install_stage(self):
        self.assertEqual(progress.map_install_stage("ExtractingPackage"), "распаковка")
        self.assertEqual(progress.map_install_stage("VerifyingApplication"), "проверка подписи")
        self.assertEqual(progress.map_install_stage(None, "upload"), "передача на устройство")
        self.assertIn("распаковка", progress.format_install(40, "распаковка"))


class InstallErrorTests(unittest.TestCase):
    def test_legacy_signature_wins(self):
        raw = (
            "ApplicationVerificationFailed: Failed to verify code signature of "
            "/tmp/Payload/Resident Cabinet.app : 0xe8008029 (The code signature version is no longer supported.)"
        )
        self.assertEqual(classify(raw), "legacy_signature")
        self.assertEqual(public_message(raw), LEGACY_TEXT)
        err = from_exception(RuntimeError(raw))
        self.assertEqual(err.kind, "legacy_signature")
        self.assertEqual(str(err), LEGACY_TEXT)
        self.assertIn("0xe8008029", err.raw)

    def test_other_codes(self):
        self.assertEqual(classify("install failed 0xe8008015 entitlements"), "entitlements")
        self.assertIn("права", public_message("0xe8008015"))
        self.assertEqual(classify("0xe800801c no valid code signature found"), "signature")
        self.assertEqual(classify("This app requires iOS 18.0 (MinimumOSVersion)"), "min_os")
        self.assertIn("более новую iOS", public_message("MinimumOSVersion 18.0"))
        self.assertEqual(classify("There is not enough disk space to install"), "space")
        self.assertIn("недостаточно места", public_message("no space left on device"))


def _cd_blob(version: int, hash_type: int, length: int = 64) -> bytes:
    # minimal CodeDirectory: 40 byte header + padding
    body = struct.pack(">IIIIIIIII", 0xFADE0C02, length, version, 0, 0, 0, 0, 0, 0)
    body += bytes([20, hash_type, 0, 12])  # hashSize, hashType, platform, pageSize
    return body + b"\x00" * (length - len(body))


def _superblob(slots: list[tuple[int, bytes]]) -> bytes:
    count = len(slots)
    header_len = 12 + 8 * count
    parts = []
    offset = header_len
    index = []
    for slot, blob in slots:
        index.append((slot, offset))
        parts.append(blob)
        offset += len(blob)
    total = offset
    data = struct.pack(">III", 0xFADE0CC0, total, count)
    for slot, off in index:
        data += struct.pack(">II", slot, off)
    return data + b"".join(parts)


class CodeSignTests(unittest.TestCase):
    def test_modern_signature_ok(self):
        cd = _cd_blob(0x20500, 2, 80)
        der = struct.pack(">II", 0xFADE7172, 16) + b"\x00" * 8
        blob = _superblob([(0, cd), (7, der)])
        parsed = parse_superblob(blob)
        self.assertTrue(parsed["has_sha256"])
        self.assertTrue(parsed["has_der"])
        self.assertGreaterEqual(parsed["cd_version"], MIN_CD_VERSION)
        self.assertFalse(codesign._is_legacy(parsed))

    def test_sha1_only_is_legacy(self):
        cd = _cd_blob(0x20200, 1, 80)
        blob = _superblob([(0, cd)])
        parsed = parse_superblob(blob)
        self.assertTrue(codesign._is_legacy(parsed))
        self.assertFalse(parsed["has_sha256"])

    def test_old_version_is_legacy(self):
        cd = _cd_blob(0x20200, 2, 80)
        der = struct.pack(">II", 0xFADE7172, 16) + b"\x00" * 8
        blob = _superblob([(0, cd), (7, der)])
        self.assertTrue(codesign._is_legacy(parse_superblob(blob)))

    def test_missing_der_is_legacy(self):
        cd = _cd_blob(0x20500, 2, 80)
        blob = _superblob([(0, cd)])
        self.assertTrue(codesign._is_legacy(parse_superblob(blob)))


class ItunesFallbackTests(unittest.TestCase):
    def test_lookup_anywhere_falls_back(self):
        chatgpt = "6448311069"

        def fake_get(url: str) -> bytes:
            if "country=ru" in url and "id=" in url:
                return json.dumps({"resultCount": 0, "results": []}).encode()
            if "country=us" in url and chatgpt in url:
                return json.dumps({"resultCount": 1, "results": [{
                    "trackId": int(chatgpt),
                    "trackName": "ChatGPT",
                    "bundleId": "com.openai.chat",
                    "artistName": "OpenAI",
                    "artworkUrl512": "https://example.com/chatgpt.png",
                    "formattedPrice": "Free",
                }]}).encode()
            return json.dumps({"resultCount": 0, "results": []}).encode()

        with mock.patch.object(itunes, "_get", side_effect=fake_get), \
             mock.patch.object(itunes, "_miss_path", return_value=Path(tempfile.gettempdir()) / "ras-miss-test.json"):
            miss = Path(tempfile.gettempdir()) / "ras-miss-test.json"
            if miss.exists():
                miss.unlink()
            found = itunes.lookup_anywhere([chatgpt], prefer="ru")
            self.assertIn(chatgpt, found)
            self.assertEqual(found[chatgpt]["name"], "ChatGPT")
            self.assertEqual(found[chatgpt]["developer"], "OpenAI")
            self.assertTrue(found[chatgpt]["icon"].startswith("https://"))
            self.assertEqual(found[chatgpt]["country"], "us")
            # без fallback — пусто
            empty = itunes.lookup_many([chatgpt], "ru", fallback=False)
            self.assertEqual(empty, {})


class VersionOrderTests(unittest.TestCase):
    def test_next_newer(self):
        from restore_gui.backend import _version_sort_key
        rows = [
            {"value": "10", "title": "1.0", "displayVersion": "1.0", "sub": "2018-01-01"},
            {"value": "20", "title": "2.0", "displayVersion": "2.0", "sub": "2021-06-01"},
            {"value": "30", "title": "3.0", "displayVersion": "3.0", "sub": "2024-03-01"},
        ]
        ordered = sorted(rows, key=_version_sort_key)
        self.assertEqual([row["value"] for row in ordered], ["10", "20", "30"])


if __name__ == "__main__":
    unittest.main()
