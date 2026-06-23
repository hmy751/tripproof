from __future__ import annotations

from typing import Any

ObservationStepStatus = str


def derive_parent_status(children: list[Any]) -> ObservationStepStatus:
    if any(child.status == "failed" for child in children):
        return "failed"
    if any(child.status == "succeeded" for child in children):
        return "succeeded"
    return "not_started"


def first_child_failure(children: list[Any]) -> Any | None:
    for child in children:
        if child.failure_kind is not None:
            return child.failure_kind
        nested = first_child_failure(child.children)
        if nested is not None:
            return nested
    return None


def find_step(step: Any, name: str) -> Any | None:
    if step.name == name:
        return step
    for child in step.children:
        match = find_step(child, name)
        if match is not None:
            return match
    return None


def merge_safe_facts(
    *,
    allowed_keys: set[str],
    current: dict[str, Any],
    updates: dict[str, Any],
    allow_string_lists: bool = False,
    allow_json_values: bool = False,
) -> dict[str, Any]:
    return {
        **safe_facts(
            allowed_keys=allowed_keys,
            facts=current,
            allow_string_lists=allow_string_lists,
            allow_json_values=allow_json_values,
        ),
        **safe_facts(
            allowed_keys=allowed_keys,
            facts=updates,
            allow_string_lists=allow_string_lists,
            allow_json_values=allow_json_values,
        ),
    }


def safe_facts(
    *,
    allowed_keys: set[str],
    facts: dict[str, Any],
    allow_string_lists: bool = False,
    allow_json_values: bool = False,
) -> dict[str, Any]:
    return {
        key: value
        for key, value in facts.items()
        if key in allowed_keys
        and is_safe_fact_value(
            value,
            allow_string_lists=allow_string_lists,
            allow_json_values=allow_json_values,
        )
    }


def is_safe_fact_value(
    value: Any,
    *,
    allow_string_lists: bool = False,
    allow_json_values: bool = False,
) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, dict):
        if allow_json_values:
            return all(
                isinstance(key, str)
                and is_safe_fact_value(item, allow_json_values=True)
                for key, item in value.items()
            )
        return all(
            isinstance(key, str) and isinstance(item, int)
            for key, item in value.items()
        )
    if isinstance(value, list) and allow_json_values:
        return all(is_safe_fact_value(item, allow_json_values=True) for item in value)
    # list는 기본 차단(redaction guard). allow_string_lists는 ready_material_ids 같은
    # string list fact를 emit하는 question observation에 한해서만 켠다.
    if isinstance(value, list) and allow_string_lists:
        return all(isinstance(item, str) for item in value)
    return False
