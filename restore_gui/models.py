
"""Списки приложений и файлов для QML (роли совпадают с полями делегатов)."""
from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

APP_ROLES = {
    Qt.UserRole + 1: "appId",
    Qt.UserRole + 2: "title",
    Qt.UserRole + 3: "sub",
    Qt.UserRole + 4: "letter",
    Qt.UserRole + 5: "tint",
    Qt.UserRole + 6: "icon",
    Qt.UserRole + 7: "status",
    Qt.UserRole + 8: "statusKind",
    Qt.UserRole + 9: "selected",
    Qt.UserRole + 10: "copies",
}

FILE_ROLES = {
    Qt.UserRole + 1: "path",
    Qt.UserRole + 2: "title",
    Qt.UserRole + 3: "info",
    Qt.UserRole + 4: "letter",
    Qt.UserRole + 5: "tint",
    Qt.UserRole + 6: "icon",
}

VERSION_ROLES = {
    Qt.UserRole + 1: "value",
    Qt.UserRole + 2: "title",
    Qt.UserRole + 3: "sub",
    Qt.UserRole + 4: "mine",
    Qt.UserRole + 5: "legacy",
    Qt.UserRole + 6: "note",
}

STOREFRONT_ROLES = {
    Qt.UserRole + 1: "value",
    Qt.UserRole + 2: "title",
}

ACCOUNT_ROLES = {
    Qt.UserRole + 1: "id",
    Qt.UserRole + 2: "email",
    Qt.UserRole + 3: "storefront",
    Qt.UserRole + 4: "storefrontName",
    Qt.UserRole + 5: "current",
    Qt.UserRole + 6: "logged",
}

JOB_ROLES = {
    Qt.UserRole + 1: "title",
    Qt.UserRole + 2: "phase",
    Qt.UserRole + 3: "downloadText",
    Qt.UserRole + 4: "installText",
    Qt.UserRole + 5: "downloadPct",
    Qt.UserRole + 6: "installPct",
    Qt.UserRole + 7: "state",
    Qt.UserRole + 8: "appId",
}


class DictList(QAbstractListModel):
    def __init__(self, roles: dict, parent=None):
        super().__init__(parent)
        self._roles = roles
        self._rows: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def roleNames(self):
        return {key: name.encode("utf-8") for key, name in self._roles.items()}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        name = self._roles.get(role)
        if not name:
            return None
        value = self._rows[index.row()].get(name)
        if name in ("selected", "mine", "legacy", "current", "logged"):
            return bool(value)
        if name in ("downloadPct", "installPct"):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
        return "" if value is None else value

    def replace(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = [dict(row) for row in rows]
        self.endResetModel()

    def at(self, row: int) -> dict | None:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def toggle(self, row: int) -> None:
        item = self.at(row)
        if item is None:
            return
        item["selected"] = not bool(item.get("selected"))
        idx = self.index(row)
        self.dataChanged.emit(idx, idx, [key for key, name in self._roles.items() if name == "selected"])

    def clear_selection(self) -> None:
        roles = [key for key, name in self._roles.items() if name == "selected"]
        for i, item in enumerate(self._rows):
            if item.get("selected"):
                item["selected"] = False
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, roles)

    def selected_rows(self) -> list[dict]:
        return [dict(item) for item in self._rows if item.get("selected")]

    def __len__(self):
        return len(self._rows)

    def patch_by_id(self, app_id: str, **fields) -> None:
        roles = [key for key, name in self._roles.items() if name in fields]
        for i, item in enumerate(self._rows):
            if str(item.get("appId") or item.get("id") or "") != str(app_id):
                continue
            item.update(fields)
            idx = self.index(i)
            self.dataChanged.emit(idx, idx, roles or None)

    def patch_by_value(self, value: str, **fields) -> None:
        roles = [key for key, name in self._roles.items() if name in fields]
        for i, item in enumerate(self._rows):
            if str(item.get("value") or "") != str(value):
                continue
            item.update(fields)
            idx = self.index(i)
            self.dataChanged.emit(idx, idx, roles or None)
