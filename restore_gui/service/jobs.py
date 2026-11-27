"""Ключи очереди загрузок: один активный набор, без дублей одной версии."""
from __future__ import annotations


def job_key(app_id, version: str | None = "") -> str:
    return f"{str(app_id or '').strip()}:{str(version or 'latest').strip() or 'latest'}"


def keys_of(rows: list[dict]) -> list[str]:
    out = []
    for item in rows or []:
        out.append(job_key(item.get("appId") or item.get("id"), item.get("version") or item.get("externalVersionId")))
    return out


def has_overlap(active: set[str] | list[str], rows: list[dict]) -> list[str]:
    running = set(active or [])
    return [key for key in keys_of(rows) if key in running]
