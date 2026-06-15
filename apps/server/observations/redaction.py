from __future__ import annotations

from pathlib import Path
from typing import Any


def export_safe_facts(step_name: str, facts: dict[str, Any]) -> dict[str, Any]:
    exported: dict[str, Any] = {}
    for key, value in facts.items():
        if step_name == "upload_snapshot" and key == "file_name":
            exported.update(file_name_summary(value))
            continue
        if is_export_safe_value(value):
            exported[key] = value
    return exported


def file_name_summary(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or value == "":
        return {"file_name_present": False, "file_extension": None}
    suffix = Path(value).suffix.lower()
    return {
        "file_name_present": True,
        "file_extension": suffix[1:] if suffix else None,
    }


def is_export_safe_value(value: Any) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and is_export_safe_value(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return all(is_export_safe_value(item) for item in value)
    return False
