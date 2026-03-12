"""Output validators for each pipeline phase."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tag_vocab import TagVocab


def _try_parse_json(text: str) -> tuple[dict | list | None, str | None]:
    """Try to parse JSON from text, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"


def _validate_phase_1_desc(data: dict, errors: list[str]) -> None:
    if "desc" not in data:
        errors.append("Missing 'desc' field")
    elif len(data["desc"]) > 50:
        pass  # Truncate silently, don't retry


def _validate_phase_1_tags(
    data: dict,
    errors: list[str],
    vocab: TagVocab | None,
) -> None:
    tags = data.get("tags")
    if tags is None:
        errors.append("Missing 'tags' field")
        return
    if not isinstance(tags, list):
        errors.append("'tags' must be an array")
        return
    if vocab is None:
        return

    from ..tag_vocab import is_valid_new_tag

    for tag in tags:
        if not vocab.contains(tag) and not is_valid_new_tag(tag):
            errors.append(f"Tag '{tag}' not in vocab and invalid as new tag")


def _validate_phase_1_signatures(
    data: dict,
    errors: list[str],
    expected_sig_count: int,
) -> None:
    signatures = data.get("signatures")
    if signatures is None:
        errors.append("Missing 'signatures' field")
        return
    if not isinstance(signatures, list):
        errors.append("'signatures' must be an array")
        return
    if len(signatures) != expected_sig_count:
        errors.append(
            f"signatures count {len(signatures)} "
            f"!= expected {expected_sig_count}"
        )


def validate_phase_1(
    text: str,
    expected_sig_count: int,
    vocab: TagVocab | None = None,
) -> list[str]:
    """Validate Phase 1 output.

    When vocab is provided, enforces that all tags exist in the
    vocabulary or satisfy new-tag naming rules.
    """
    errors = []
    data, err = _try_parse_json(text)
    if err:
        return [err]

    if not isinstance(data, dict):
        return ["Output must be a JSON object"]

    _validate_phase_1_desc(data, errors)
    _validate_phase_1_tags(data, errors, vocab)
    _validate_phase_1_signatures(data, errors, expected_sig_count)

    return errors


def validate_phase_2a(text: str) -> list[str]:
    """Validate Phase 2a output (module vocab)."""
    errors = []
    data, err = _try_parse_json(text)
    if err:
        return [err]

    if not isinstance(data, dict):
        return ["Output must be a JSON object"]

    modules = data.get("modules")
    if not isinstance(modules, list):
        return ["Missing or invalid 'modules' array"]

    if len(modules) < 8 or len(modules) > 15:
        errors.append(
            f"modules count {len(modules)}, should be 8-15"
        )

    for m in modules:
        mid = m.get("id", "")
        if not mid.startswith("mod:"):
            errors.append(f"Invalid module id: {mid}")

    return errors


def validate_phase_2b(
    text: str,
    expected_count: int,
    valid_module_ids: set[str],
) -> list[str]:
    """Validate Phase 2b output (file→module assignment)."""
    errors = []
    data, err = _try_parse_json(text)
    if err:
        return [err]

    if not isinstance(data, list):
        return ["Output must be a JSON array"]

    if len(data) != expected_count:
        errors.append(
            f"array length {len(data)} != expected {expected_count}"
        )

    for item in data:
        mid = item.get("module_id", "")
        if mid not in valid_module_ids:
            errors.append(f"Invalid module_id: {mid}")

    return errors


def validate_phase_3a(
    text: str,
    valid_files: set[str],
) -> list[str]:
    """Validate Phase 3a output (module description)."""
    errors = []
    data, err = _try_parse_json(text)
    if err:
        return [err]

    if not isinstance(data, dict):
        return ["Output must be a JSON object"]

    if "desc" not in data:
        errors.append("Missing 'desc' field")

    key_files = data.get("key_files", [])
    if not isinstance(key_files, list):
        errors.append("'key_files' must be an array")
    else:
        for f in key_files:
            if f not in valid_files:
                errors.append(f"Invalid key_file: {f}")

    return errors


def validate_phase_3b(text: str) -> list[str]:
    """Validate Phase 3b output (project overview)."""
    errors = []
    data, err = _try_parse_json(text)
    if err:
        return [err]

    if not isinstance(data, dict):
        return ["Output must be a JSON object"]

    for field in ("overview", "architecture", "scale"):
        if field not in data:
            errors.append(f"Missing '{field}' field")

    return errors
