"""Tests for hippocampus.tag_vocab — tag vocabulary system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hippocampus.tag_vocab import (
    TagVocab,
    default_vocab,
    is_valid_new_tag,
    load_vocab,
    save_vocab,
)
from hippocampus.llm.validators import validate_phase_1


class TestDefaultVocab:
    def test_has_four_dimensions(self):
        vocab = default_vocab()
        assert set(vocab.keys()) == {"role", "domain", "pattern", "tech"}

    def test_each_dimension_non_empty(self):
        vocab = default_vocab()
        for dim, tags in vocab.items():
            assert len(tags) > 0, f"Dimension '{dim}' is empty"

    def test_all_tags_lowercase(self):
        vocab = default_vocab()
        for dim, tags in vocab.items():
            for tag in tags:
                assert tag == tag.lower(), f"Tag '{tag}' in '{dim}' not lowercase"

    def test_role_dimension_contents(self):
        vocab = default_vocab()
        expected = {"entrypoint", "lib", "config", "test", "docs", "ci", "script", "asset"}
        assert set(vocab["role"]) == expected

    def test_tech_dimension_contents(self):
        vocab = default_vocab()
        assert "python" in vocab["tech"]
        assert "typescript" in vocab["tech"]
        assert "rust" in vocab["tech"]


class TestTagVocab:
    def test_contains_base_tags(self):
        v = TagVocab(default_vocab())
        assert v.contains("python")
        assert v.contains("entrypoint")
        assert v.contains("cli")

    def test_not_contains_unknown(self):
        v = TagVocab(default_vocab())
        assert not v.contains("nonexistent-xyz")

    def test_all_tags_returns_flat_set(self):
        v = TagVocab(default_vocab())
        tags = v.all_tags()
        assert isinstance(tags, set)
        assert "python" in tags
        assert "entrypoint" in tags
        assert len(tags) > 30  # 4 dimensions, each with multiple tags

    def test_add_tag_new(self):
        v = TagVocab(default_vocab())
        assert v.add_tag("my-new-tag") is True
        assert v.contains("my-new-tag")
        assert "my-new-tag" in v.all_tags()

    def test_add_tag_duplicate(self):
        v = TagVocab(default_vocab())
        assert v.add_tag("python") is False  # already exists

    def test_add_tag_invalid_name(self):
        v = TagVocab(default_vocab())
        assert v.add_tag("UPPERCASE") is False
        assert not v.contains("UPPERCASE")

    def test_add_tag_custom_dimension(self):
        v = TagVocab(default_vocab())
        v.add_tag("my-tag", dimension="custom")
        snap = v.snapshot()
        assert "my-tag" in snap["custom"]

    def test_validate_tags_all_valid(self):
        v = TagVocab(default_vocab())
        valid, invalid = v.validate_tags(["python", "cli", "lib"])
        assert valid == ["python", "cli", "lib"]
        assert invalid == []

    def test_validate_tags_mixed(self):
        v = TagVocab(default_vocab())
        valid, invalid = v.validate_tags(["python", "unknown-x"])
        assert valid == ["python"]
        assert invalid == ["unknown-x"]

    def test_validate_tags_all_invalid(self):
        v = TagVocab(default_vocab())
        valid, invalid = v.validate_tags(["nope", "nada"])
        assert valid == []
        assert invalid == ["nope", "nada"]

    def test_content_hash_deterministic(self):
        v1 = TagVocab(default_vocab())
        v2 = TagVocab(default_vocab())
        assert v1.content_hash() == v2.content_hash()

    def test_content_hash_changes_on_add(self):
        v = TagVocab(default_vocab())
        h1 = v.content_hash()
        v.add_tag("brand-new")
        h2 = v.content_hash()
        assert h1 != h2

    def test_snapshot_roundtrip(self):
        v = TagVocab(default_vocab())
        v.add_tag("extra-tag", dimension="custom")
        snap = v.snapshot()
        v2 = TagVocab(snap)
        assert v2.contains("extra-tag")
        assert v2.contains("python")
        assert v.content_hash() == v2.content_hash()

    def test_format_for_prompt(self):
        v = TagVocab({"role": ["lib", "test"], "tech": ["python"]})
        text = v.format_for_prompt()
        assert "role:" in text
        assert "tech:" in text
        assert "python" in text


class TestNewTagRule:
    def test_valid_simple(self):
        assert is_valid_new_tag("mylib") is True

    def test_valid_with_hyphen(self):
        assert is_valid_new_tag("my-lib") is True

    def test_valid_with_digits(self):
        assert is_valid_new_tag("lib2") is True

    def test_invalid_uppercase(self):
        assert is_valid_new_tag("MyLib") is False

    def test_invalid_too_long(self):
        assert is_valid_new_tag("a" * 16) is False

    def test_valid_max_length(self):
        assert is_valid_new_tag("a" * 15) is True

    def test_invalid_empty(self):
        assert is_valid_new_tag("") is False

    def test_invalid_starts_with_digit(self):
        assert is_valid_new_tag("1abc") is False

    def test_invalid_starts_with_hyphen(self):
        assert is_valid_new_tag("-abc") is False

    def test_invalid_special_chars(self):
        assert is_valid_new_tag("my_lib") is False
        assert is_valid_new_tag("my.lib") is False
        assert is_valid_new_tag("my lib") is False


class TestVocabIO:
    def test_save_and_load_roundtrip(self, tmp_path):
        v = TagVocab(default_vocab())
        v.add_tag("extra-one", dimension="custom")
        save_vocab(tmp_path, v)

        v2 = load_vocab(tmp_path)
        assert v2.contains("python")
        assert v2.contains("extra-one")
        assert v.content_hash() == v2.content_hash()

    def test_load_missing_file_returns_default(self, tmp_path):
        v = load_vocab(tmp_path)
        assert v.contains("python")
        assert v.contains("entrypoint")
        dv = TagVocab(default_vocab())
        assert v.content_hash() == dv.content_hash()

    def test_save_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "sub" / "dir"
        v = TagVocab(default_vocab())
        save_vocab(nested, v)
        v2 = load_vocab(nested)
        assert v2.contains("python")


class TestValidatorIntegration:
    """Test validate_phase_1 with vocab parameter."""

    def test_valid_tags_from_vocab(self):
        v = TagVocab(default_vocab())
        text = json.dumps({
            "desc": "Helper utilities",
            "tags": ["python", "lib", "cli"],
            "signatures": [],
        })
        errors = validate_phase_1(text, expected_sig_count=0, vocab=v)
        assert errors == []

    def test_invalid_tag_not_in_vocab(self):
        v = TagVocab(default_vocab())
        text = json.dumps({
            "desc": "Helper utilities",
            "tags": ["python", "INVALID_TAG"],
            "signatures": [],
        })
        errors = validate_phase_1(text, expected_sig_count=0, vocab=v)
        assert any("INVALID_TAG" in e for e in errors)

    def test_new_tag_proposal_accepted(self):
        """A new tag that meets naming rules should pass validation."""
        v = TagVocab(default_vocab())
        text = json.dumps({
            "desc": "Helper utilities",
            "tags": ["python", "my-new-tag"],
            "signatures": [],
        })
        errors = validate_phase_1(text, expected_sig_count=0, vocab=v)
        assert errors == []

    def test_no_vocab_skips_tag_check(self):
        """Without vocab, any tags pass (backward compat)."""
        text = json.dumps({
            "desc": "Helper utilities",
            "tags": ["anything", "GOES_HERE"],
            "signatures": [],
        })
        errors = validate_phase_1(text, expected_sig_count=0, vocab=None)
        assert errors == []

    def test_mixed_valid_and_invalid_tags(self):
        v = TagVocab(default_vocab())
        text = json.dumps({
            "desc": "ok",
            "tags": ["python", "Bad Tag!", "cli"],
            "signatures": [],
        })
        errors = validate_phase_1(text, expected_sig_count=0, vocab=v)
        assert len(errors) == 1
        assert "Bad Tag!" in errors[0]
