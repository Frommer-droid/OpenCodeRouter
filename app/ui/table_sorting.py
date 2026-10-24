from __future__ import annotations

import re
from datetime import datetime
from ipaddress import ip_address
from typing import Any

RUSSIAN_LETTER = re.compile(r"[а-яё]", re.IGNORECASE)


def _node_name_sort_key(value: str) -> str:
    normalized = value.strip().casefold()
    russian_name = RUSSIAN_LETTER.search(normalized)
    return normalized[russian_name.start() :] if russian_name else normalized


def _sort_value(row: dict[str, Any], column: int) -> object | None:
    if column == 0:
        value = str(row.get("Node") or "").strip()
        return _node_name_sort_key(value) if value else None
    if column == 1:
        value = str(row.get("IP") or "").strip()
        try:
            return int(ip_address(value))
        except ValueError:
            return None
    if column == 2:
        value = str(row.get("API") or "").upper()
        return {"OK": 0, "FAIL": 1}.get(value)
    if column == 3:
        try:
            return float(row["LatencyMs"]) if row.get("LatencyMs") is not None else None
        except (TypeError, ValueError):
            return None
    if column == 4:
        value = str(row.get("CheckedUtc") or "").strip()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            return None
    return None


def sort_node_rows(
    rows: list[dict[str, Any]], column: int, *, descending: bool = False
) -> list[dict[str, Any]]:
    present: list[tuple[object, str, dict[str, Any]]] = []
    missing: list[dict[str, Any]] = []
    for row in rows:
        value = _sort_value(row, column)
        if value is None:
            missing.append(row)
        else:
            present.append((value, str(row.get("Node") or "").casefold(), row))
    present.sort(key=lambda entry: (entry[0], entry[1]), reverse=descending)
    missing.sort(key=lambda row: str(row.get("Node") or "").casefold())
    return [entry[2] for entry in present] + missing
