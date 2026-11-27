"""Разбор прогресса скачивания ipatool и стадий установки на устройство."""
from __future__ import annotations

import re
import time

# ipatool-cpp: "Downloading:  45% (12.3 MB/40.0 MB, 3.1 MB/s)" и похожие строки.
_PCT = re.compile(r"(\d{1,3})\s*%")
_PAIR = re.compile(
    r"\((?P<done>[0-9]+(?:[.,][0-9]+)?)\s*(?P<du>k|kb|kib|m|mb|mib|g|gb|gib)?"
    r"\s*/\s*(?P<total>[0-9]+(?:[.,][0-9]+)?)\s*(?P<tu>k|kb|kib|m|mb|mib|g|gb|gib)"
    r"(?:\s*,\s*(?P<speed>[0-9]+(?:[.,][0-9]+)?)\s*(?P<su>k|kb|kib|m|mb|mib|g|gb|gib)\s*/s)?\)",
    re.I,
)
_SPEED = re.compile(r"([0-9]+(?:[.,][0-9]+)?)\s*(k|kb|kib|m|mb|mib|g|gb|gib)\s*/s", re.I)
_DONE = re.compile(r"([0-9]+(?:[.,][0-9]+)?)\s*(k|kb|kib|m|mb|mib|g|gb|gib)\b", re.I)

_UNITS = {
    "k": 1000, "kb": 1000, "kib": 1024,
    "m": 1000 ** 2, "mb": 1000 ** 2, "mib": 1024 ** 2,
    "g": 1000 ** 3, "gb": 1000 ** 3, "gib": 1024 ** 3,
}

INSTALL_STAGES = {
    "creatingstagingdirectory": "распаковка",
    "extractingpackage": "распаковка",
    "unpacking": "распаковка",
    "inspectingpackage": "проверка подписи",
    "preflightingapplication": "проверка подписи",
    "verifyingapplication": "проверка подписи",
    "verifying": "проверка подписи",
    "takinginstalllock": "установка",
    "installing": "установка",
    "installingplaceholder": "установка",
    "generatingapplicationmap": "установка",
    "installwaiting": "установка",
    "complete": "установка",
}

STAGE_UPLOAD = "передача на устройство"
STAGE_UNPACK = "распаковка"
STAGE_SIGN = "проверка подписи"
STAGE_INSTALL = "установка"


def parse_download_progress(text: str) -> dict | None:
    """Вытащить процент, объём и скорость из вывода ipatool. None, если данных нет."""
    if not text:
        return None
    # брать последний осмысленный кусок (прогресс часто идёт через \\r)
    chunk = text.replace("\r\n", "\n")
    parts = re.split(r"[\r\n]+", chunk)
    best = None
    for part in parts:
        hit = _parse_one(part)
        if hit:
            best = hit
    return best


def _parse_one(line: str) -> dict | None:
    line = (line or "").strip()
    if not line:
        return None
    pct = None
    m = _PCT.search(line)
    if m:
        value = int(m.group(1))
        if 0 <= value <= 100:
            pct = float(value)
    done = total = speed = None
    pair = _PAIR.search(line)
    if pair:
        tu = (pair.group("tu") or "mb").lower()
        du = (pair.group("du") or tu).lower()
        done = _to_bytes(pair.group("done"), du)
        total = _to_bytes(pair.group("total"), tu)
        if pair.group("speed"):
            speed = _to_bytes(pair.group("speed"), (pair.group("su") or "mb").lower())
    if speed is None:
        sm = _SPEED.search(line)
        if sm:
            speed = _to_bytes(sm.group(1), sm.group(2).lower())
    if done is None and total is None and "download" in line.lower():
        dm = _DONE.search(line)
        if dm:
            done = _to_bytes(dm.group(1), dm.group(2).lower())
    if pct is None and done and total:
        pct = min(100.0, 100.0 * done / total)
    if pct is None and done is None and speed is None:
        return None
    return {
        "pct": pct,
        "done": done,
        "total": total,
        "speed": speed,
    }


def _to_bytes(value: str, unit: str) -> float:
    number = float(value.replace(",", "."))
    return number * _UNITS.get(unit.lower(), 1)


def format_bytes(n: float | int | None) -> str:
    if n is None:
        return ""
    n = float(n)
    if n >= 1000 ** 3:
        return f"{n / (1000 ** 3):.2f} ГБ".replace(".", ",")
    if n >= 1000 ** 2 or n == 0:
        return f"{n / (1000 ** 2):.1f} МБ".replace(".", ",")
    if n >= 1000:
        return f"{n / 1000:.0f} КБ"
    return f"{int(n)} Б"


def format_speed(n: float | int | None) -> str:
    if not n:
        return ""
    return format_bytes(n) + "/с"


def format_eta(done: float | None, total: float | None, speed: float | None) -> str:
    if not done or not total or not speed or speed <= 0 or done >= total:
        return ""
    seconds = int((total - done) / speed)
    if seconds < 1:
        return "ещё меньше секунды"
    if seconds < 60:
        return f"ещё {seconds} с"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"ещё {minutes} мин {sec} с" if sec else f"ещё {minutes} мин"
    hours, minutes = divmod(minutes, 60)
    return f"ещё {hours} ч {minutes} мин"


def format_download(pct, done, total, speed, eta: str = "") -> str:
    parts = []
    if pct is not None and pct >= 0:
        parts.append(f"{int(round(pct))} %")
    if done is not None and total:
        parts.append(f"{format_bytes(done)} / {format_bytes(total)}")
    elif done:
        parts.append(format_bytes(done))
    if speed:
        parts.append(format_speed(speed))
    if not eta:
        eta = format_eta(done, total, speed)
    if eta:
        parts.append(eta)
    return " · ".join(parts) if parts else "Скачивание…"


class SpeedMeter:
    """Скорость по росту файла, если ipatool не пишет прогресс."""

    def __init__(self):
        self.t0 = time.monotonic()
        self.last_size = 0
        self.last_t = self.t0
        self.speed = 0.0

    def update(self, size: int) -> float:
        now = time.monotonic()
        dt = now - self.last_t
        if dt >= 0.25 and size >= self.last_size:
            self.speed = (size - self.last_size) / dt
            self.last_size = size
            self.last_t = now
        elif now - self.t0 > 0.5 and size:
            self.speed = size / (now - self.t0)
        return self.speed


def map_install_stage(status: str | None, phase: str = "") -> str:
    if phase == "upload":
        return STAGE_UPLOAD
    key = (status or "").replace(" ", "").lower()
    return INSTALL_STAGES.get(key, STAGE_INSTALL if phase == "install" else (STAGE_UPLOAD if phase == "upload" else ""))


def format_install(pct, stage: str) -> str:
    bits = []
    if pct is not None and pct >= 0:
        bits.append(f"{int(round(pct))} %")
    if stage:
        bits.append(stage)
    return " · ".join(bits) if bits else "Установка…"
