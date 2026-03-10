"""Tests for hippocampus.llm.validators — output validation for each pipeline phase."""

from __future__ import annotations

import json

from hippocampus.llm.validators import (
    _try_parse_json,
    validate_phase_1,
    validate_phase_2a,
    validate_phase_2b,
    validate_phase_3a,
    validate_phase_3b,
)


class TestTryParseJson:
    def test_valid_json(self):
        data, err = _try_parse_json('{"key": "value"}')
        assert data == {"key": "value"}
        assert err is None

    def test_invalid_json(self):
        data, err = _try_parse_json("not json")
        assert data is None
        assert "JSON parse error" in err

    def test_markdown_fenced_json(self):
        text = '```json\n{"key": "value"}\n```'
        data, err = _try_parse_json(text)
        assert data == {"key": "value"}
        assert err is None

    def test_empty_string(self):
        data, err = _try_parse_json("")
        assert data is None
        assert err is not None

    def test_json_array(self):
        data, err = _try_parse_json('[1, 2, 3]')
        assert data == [1, 2, 3]
        assert err is None


class TestValidatePhase1:
    def test_valid_output(self):
        text = json.dumps({
            "desc": "Helper utilities",
            "tags": ["utils", "helper"],
            "signatures": [
                {"name": "foo", "desc": "does foo"},
            ],
        })
        errors = validate_phase_1(text, expected_sig_count=1)
        assert errors == []

    def test_missing_desc(self):
        text = json.dumps({"tags": [], "signatures": []})
        errors = validate_phase_1(text, expected_sig_count=0)
        assert any("desc" in e for e in errors)

    def test_wrong_sig_count(self):
        text = json.dumps({
            "desc": "ok",
            "tags": ["a"],
            "signatures": [{"name": "x", "desc": "y"}],
        })
        errors = validate_phase_1(text, expected_sig_count=3)
        assert any("signatures count" in e for e in errors)

    def test_invalid_json(self):
        errors = validate_phase_1("not json", expected_sig_count=0)
        assert len(errors) == 1
        assert "JSON" in errors[0]


class TestValidatePhase2a:
    def test_valid_output(self):
        modules = [{"id": f"mod:m{i}", "desc": f"module {i}"} for i in range(10)]
        text = json.dumps({"modules": modules})
        errors = validate_phase_2a(text)
        assert errors == []

    def test_too_few_modules(self):
        modules = [{"id": "mod:a", "desc": "only one"}]
        text = json.dumps({"modules": modules})
        errors = validate_phase_2a(text)
        assert any("modules count" in e for e in errors)

    def test_invalid_module_id(self):
        modules = [{"id": f"bad-id-{i}", "desc": f"m{i}"} for i in range(10)]
        text = json.dumps({"modules": modules})
        errors = validate_phase_2a(text)
        assert any("Invalid module id" in e for e in errors)


class TestValidatePhase2b:
    def test_valid_output(self):
        valid_ids = {"mod:core", "mod:utils"}
        items = [
            {"file": "a.py", "module_id": "mod:core"},
            {"file": "b.py", "module_id": "mod:utils"},
        ]
        text = json.dumps(items)
        errors = validate_phase_2b(text, expected_count=2, valid_module_ids=valid_ids)
        assert errors == []

    def test_wrong_count(self):
        valid_ids = {"mod:core"}
        items = [{"file": "a.py", "module_id": "mod:core"}]
        text = json.dumps(items)
        errors = validate_phase_2b(text, expected_count=5, valid_module_ids=valid_ids)
        assert any("array length" in e for e in errors)

    def test_invalid_module_id(self):
        valid_ids = {"mod:core"}
        items = [{"file": "a.py", "module_id": "mod:unknown"}]
        text = json.dumps(items)
        errors = validate_phase_2b(text, expected_count=1, valid_module_ids=valid_ids)
        assert any("Invalid module_id" in e for e in errors)


class TestValidatePhase3a:
    def test_valid_output(self):
        valid_files = {"src/a.py", "src/b.py", "src/c.py"}
        text = json.dumps({
            "desc": "Core module handling main logic",
            "key_files": ["src/a.py", "src/b.py"],
        })
        errors = validate_phase_3a(text, valid_files)
        assert errors == []

    def test_missing_desc(self):
        text = json.dumps({"key_files": []})
        errors = validate_phase_3a(text, set())
        assert any("desc" in e for e in errors)

    def test_invalid_key_file(self):
        valid_files = {"src/a.py"}
        text = json.dumps({
            "desc": "ok",
            "key_files": ["src/nonexistent.py"],
        })
        errors = validate_phase_3a(text, valid_files)
        assert any("Invalid key_file" in e for e in errors)


class TestValidatePhase3b:
    def test_valid_output(self):
        text = json.dumps({
            "overview": "A multi-AI collaboration framework",
            "architecture": "Plugin-based modular system",
            "scale": {"files": 110, "modules": 10, "primary_lang": "python"},
        })
        errors = validate_phase_3b(text)
        assert errors == []

    def test_missing_fields(self):
        text = json.dumps({"overview": "ok"})
        errors = validate_phase_3b(text)
        assert any("architecture" in e for e in errors)
        assert any("scale" in e for e in errors)

    def test_not_object(self):
        text = json.dumps([1, 2, 3])
        errors = validate_phase_3b(text)
        assert any("object" in e for e in errors)
