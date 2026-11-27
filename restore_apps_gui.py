#!/usr/bin/env python3
"""Точка входа оконной программы RestoreAppStore."""
from restore_gui.startup import configure, log_exception
from restore_gui.app import main

if __name__ == "__main__":
    configure()
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — у сборки без консоли ошибка иначе пропадёт
        log_exception("fatal in main", exc)
        raise
