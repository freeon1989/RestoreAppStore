"""v2.0.6: проверка IPA, очередь загрузок, Mac-only, ошибки распаковки."""
from __future__ import annotations

import io
import zipfile
import plistlib
from pathlib import Path

import pytest

from restore_gui.service import ipa as ipa_svc
from restore_gui.service import jobs as jobs_svc
from restore_gui.service import platform as platform_svc
from restore_gui.service.install_errors import classify, public_message
from restore_gui.service.store import Store, StoreError, _cache_get, _cache_put, _begin_enrich, _end_enrich


def _ipa_bytes(platform: str = "ios", name: str = "Foo") -> bytes:
    plist = {
        "CFBundleDisplayName": name,
        "CFBundleName": name,
        "CFBundleIdentifier": "com.example.foo",
        "CFBundleShortVersionString": "1.2.3",
        "CFBundleVersion": "123",
    }
    if platform == "ios":
        plist["DTPlatformName"] = "iphoneos"
        plist["LSRequiresIPhoneOS"] = True
        inner = f"Payload/{name}.app/Info.plist"
    else:
        plist["DTPlatformName"] = "macosx"
        plist["LSRequiresIPhoneOS"] = False
        inner = f"Payload/{name}.app/Info.plist"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(inner, plistlib.dumps(plist))
        zf.writestr(f"Payload/{name}.app/PkgInfo", b"APPL????")
    return buf.getvalue()


def _write_ipa(path: Path, platform: str = "ios", name: str = "Foo") -> Path:
    path.write_bytes(_ipa_bytes(platform, name))
    return path


def test_validate_good_zip(tmp_path):
    path = _write_ipa(tmp_path / "WireGuard.ipa")
    result = ipa_svc.validate(path)
    assert result["ok"] is True
    assert result["platform"] == "ios"
    assert result["size"] > 0


def test_validate_truncated_zip_without_eocd(tmp_path):
    path = tmp_path / "WireGuard.ipa"
    # как на компьютере Дмитрия: 5 МБ без центрального каталога
    path.write_bytes(b"PK\x03\x04" + b"\x00" * 2000)
    result = ipa_svc.validate(path)
    assert result["ok"] is False
    assert "повреждён" in result["error"]


def test_validate_missing_payload(tmp_path):
    path = tmp_path / "empty.ipa"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("README.txt", "no payload")
    path.write_bytes(buf.getvalue())
    result = ipa_svc.validate(path)
    assert result["ok"] is False


def test_validate_expected_size_too_small(tmp_path):
    path = _write_ipa(tmp_path / "tiny.ipa")
    # файл нормальный, но прогресс обещал ~20 МБ
    result = ipa_svc.validate(path, expected_size=20 * 1024 * 1024)
    assert result["ok"] is False
    assert "повреждён" in result["error"]


def test_inspect_reads_plist(tmp_path):
    path = _write_ipa(tmp_path / "App.ipa", name="ChatGPT")
    info = ipa_svc.inspect(path)
    assert info["name"] == "ChatGPT"
    assert info["bundle"] == "com.example.foo"
    assert info["version"] == "1.2.3"
    assert info["platform"] == "ios"


def test_staging_paths_are_unique(tmp_path):
    a = ipa_svc.staging_path(tmp_path, "1451685025", "830205416", title="WireGuard")
    b = ipa_svc.staging_path(tmp_path, "1451685025", "830205416", title="WireGuard")
    assert a != b
    assert a.parent == tmp_path
    assert "downloading" in a.name
    assert a.suffix == ".ipa"
    assert ipa_svc.is_temp_name(a)
    assert not ipa_svc.is_temp_name(tmp_path / "WireGuard.ipa")


def test_temp_name_patterns():
    assert ipa_svc.is_temp_name("WireGuard.ipa.tmp")
    assert ipa_svc.is_temp_name("Xcode.ipa.tmp.dl-26744-abcdef")
    assert ipa_svc.is_temp_name("WireGuard.downloading-145-830-ab.ipa")
    assert not ipa_svc.is_temp_name("WireGuard.ipa")
    assert not ipa_svc.is_temp_name("Дом с Алисой.ipa")


def test_list_files_skips_temps(tmp_path):
    _write_ipa(tmp_path / "ChatGPT.ipa", name="ChatGPT")
    (tmp_path / "WireGuard.ipa.tmp").write_bytes(b"partial")
    (tmp_path / "ChatGPT.downloading-1-1-aa.ipa").write_bytes(b"partial")
    rows = ipa_svc.list_files(tmp_path)
    names = {r["title"] for r in rows}
    assert "ChatGPT" in names
    assert all("downloading" not in r["path"] and not r["path"].endswith(".tmp") for r in rows)


def test_clean_small_temps_keeps_huge(tmp_path):
    small = tmp_path / "WireGuard.ipa.tmp"
    small.write_bytes(b"x" * 100)
    huge = tmp_path / "Xcode.ipa.tmp.dl-26744-ffff"
    huge.write_bytes(b"y" * (ipa_svc.HUGE_TEMP_BYTES + 10))
    result = ipa_svc.clean_temps(tmp_path, include_huge=False)
    assert not small.exists()
    assert huge.exists()
    assert result["deleted"] == 1
    assert len(result["leftover"]) == 1
    hint = ipa_svc.leftover_hint(result["leftover"])
    assert "Xcode" in hint
    result2 = ipa_svc.clean_temps(tmp_path, include_huge=True)
    assert not huge.exists()
    assert result2["deleted"] == 1


def test_find_output_prefers_valid_zip(tmp_path):
    dest = tmp_path / "WireGuard.downloading-1-1-aa.ipa"
    dest.write_bytes(b"PK\x03\x04" + b"\x00" * 100)  # битый
    good = Path(str(dest) + ".tmp")
    _write_ipa(good, name="WG")
    found = ipa_svc.find_output(dest)
    assert found == good
    published = ipa_svc.publish(found, tmp_path / "WireGuard.ipa")
    assert published == tmp_path / "WireGuard.ipa"
    assert published.is_file()
    assert not good.exists()


def test_platform_from_itunes_mac():
    assert platform_svc.from_metadata({"kind": "mac-software"}) == "mac"
    assert platform_svc.from_metadata({"storeKind": "mac-software"}) == "mac"
    assert platform_svc.from_metadata({"kind": "software"}) == "ios"
    assert platform_svc.from_metadata({"software-platform": "software-platform.macos"}) == "mac"
    assert platform_svc.is_mac({"kind": "mac-software"})
    assert not platform_svc.is_mac({"kind": "software", "supportedDevices": ["iPhone14,5", "iPad8,1"]})


def test_platform_from_plist():
    assert platform_svc.from_plist({"DTPlatformName": "macosx"}) == "mac"
    assert platform_svc.from_plist({"DTPlatformName": "iphoneos", "LSRequiresIPhoneOS": True}) == "ios"


def test_validate_mac_ipa_ok_but_marked(tmp_path):
    path = _write_ipa(tmp_path / "Xcode.ipa", platform="mac", name="Xcode")
    result = ipa_svc.validate(path)
    assert result["ok"] is True
    assert result["platform"] == "mac"
    assert ipa_svc.inspect(path)["platform"] == "mac"


def test_package_extraction_message():
    raw = "PackageExtractionFailed: Could not extract archive"
    assert classify(raw) == "package_extract"
    assert public_message(raw) == ipa_svc.CORRUPT_TEXT
    assert "скачиваю заново" in public_message(raw)


def test_job_key_and_overlap():
    assert jobs_svc.job_key("1451685025", "830205416") == "1451685025:830205416"
    rows = [{"appId": "1451685025", "version": "830205416"}]
    assert jobs_svc.has_overlap({"1451685025:830205416"}, rows)
    assert not jobs_svc.has_overlap({"other:1"}, rows)
    assert jobs_svc.has_overlap(set(), rows) == []


def test_version_cache_write_through(tmp_path, monkeypatch):
    from restore_gui.service import paths
    monkeypatch.setattr(paths, "logs_dir", lambda: tmp_path)
    _cache_put("497799835:1", {"displayVersion": "16.0", "sub": "2024-01-01"})
    got = _cache_get("497799835:1")
    assert got["displayVersion"] == "16.0"
    assert (tmp_path / "cache" / "versions.json").is_file()


def test_enrich_dedupe_second_call():
    assert _begin_enrich("497799835:") is True
    assert _begin_enrich("497799835:") is False
    assert _begin_enrich("6448311069:") is True
    _end_enrich("497799835:")
    _end_enrich("6448311069:")
    assert _begin_enrich("497799835:") is True
    _end_enrich("497799835:")


def test_download_verified_retries_once(tmp_path):
    store = Store.__new__(Store)
    calls = []

    def fake_download(dest, **kwargs):
        calls.append(Path(dest))
        if len(calls) == 1:
            Path(dest).write_bytes(b"PK\x03\x04" + b"\x00" * 500)
            return Path(dest)
        return _write_ipa(Path(dest), name="WireGuard")

    store.download = fake_download
    path = Store.download_verified(store, tmp_path, title="WireGuard", app_id="1451685025", version_id="830205416")
    assert path == tmp_path / "WireGuard.ipa"
    assert ipa_svc.validate(path)["ok"]
    assert len(calls) == 2
    assert calls[0] != calls[1]
    # временные файлы убраны
    leftovers = [p for p in tmp_path.iterdir() if ipa_svc.is_temp_name(p)]
    assert leftovers == []


def test_download_verified_fails_after_two_bad(tmp_path):
    store = Store.__new__(Store)

    def fake_download(dest, **kwargs):
        Path(dest).write_bytes(b"PK\x03\x04" + b"\x00" * 500)
        return Path(dest)

    store.download = fake_download
    with pytest.raises(StoreError) as exc:
        Store.download_verified(store, tmp_path, title="WireGuard", app_id="1451685025")
    assert "повреждён" in str(exc.value)
