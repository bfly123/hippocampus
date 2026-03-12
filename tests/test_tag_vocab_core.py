"""Core tests for hippocampus.tag_vocab."""

from __future__ import annotations

import json

from hippocampus.llm.validators import validate_phase_1
from hippocampus.tag_vocab import TagVocab, default_vocab, is_valid_new_tag


class TestDefaultVocab:
    def test_has_four_dimensions(self):
        assert set(default_vocab().keys()) == {"role", "domain", "pattern", "tech"}

    def test_each_dimension_non_empty(self):
        for dimension, tags in default_vocab().items():
            assert len(tags) > 0, f"Dimension '{dimension}' is empty"

    def test_all_tags_lowercase(self):
        for dimension, tags in default_vocab().items():
            for tag in tags:
                assert tag == tag.lower(), f"Tag '{tag}' in '{dimension}' not lowercase"

    def test_role_dimension_contents(self):
        expected = {"entrypoint", "lib", "config", "test", "docs", "ci", "script", "asset"}
        assert set(default_vocab()["role"]) == expected

    def test_tech_dimension_contents(self):
        vocab = default_vocab()
        assert "python" in vocab["tech"]
        assert "typescript" in vocab["tech"]
        assert "rust" in vocab["tech"]


class TestTagVocabContains:
    def test_contains_base_tags(self):
        vocab = TagVocab(default_vocab())
        assert vocab.contains("python")
        assert vocab.contains("entrypoint")
        assert vocab.contains("cli")

    def test_not_contains_unknown(self):
        assert not TagVocab(default_vocab()).contains("nonexistent-xyz")

    def test_all_tags_returns_flat_set(self):
        tags = TagVocab(default_vocab()).all_tags()
        assert isinstance(tags, set)
        assert "python" in tags
        assert "entrypoint" in tags
        assert len(tags) > 30


class TestTagVocabMutation:
    def test_add_tag_new(self):
        vocab = TagVocab(default_vocab())
        assert vocab.add_tag("my-new-tag") is True
        assert vocab.contains("my-new-tag")
        assert "my-new-tag" in vocab.all_tags()

    def test_add_tag_duplicate(self):
        assert TagVocab(default_vocab()).add_tag("python") is False

    def test_add_tag_invalid_name(self):
        vocab = TagVocab(default_vocab())
        assert vocab.add_tag("UPPERCASE") is False
        assert not vocab.contains("UPPERCASE")

    def test_add_tag_custom_dimension(self):
        vocab = TagVocab(default_vocab())
        vocab.add_tag("my-tag", dimension="custom")
        assert "my-tag" in vocab.snapshot()["custom"]

    def test_content_hash_deterministic(self):
        assert TagVocab(default_vocab()).content_hash() == TagVocab(default_vocab()).content_hash()

    def test_content_hash_changes_on_add(self):
        vocab = TagVocab(default_vocab())
        h1 = vocab.content_hash()
        vocab.add_tag("brand-new")
        assert h1 != vocab.content_hash()

    def test_snapshot_roundtrip(self):
        vocab = TagVocab(default_vocab())
        vocab.add_tag("extra-tag", dimension="custom")
        restored = TagVocab(vocab.snapshot())
        assert restored.contains("extra-tag")
        assert restored.contains("python")
        assert vocab.content_hash() == restored.content_hash()

    def test_format_for_prompt(self):
        text = TagVocab({"role": ["lib", "test"], "tech": ["python"]}).format_for_prompt()
        assert "role:" in text
        assert "tech:" in text
        assert "python" in text


class TestTagValidation:
    def test_validate_tags_all_valid(self):
        valid, invalid = TagVocab(default_vocab()).validate_tags(["python", "cli", "lib"])
        assert valid == ["python", "cli", "lib"]
        assert invalid == []

    def test_validate_tags_mixed(self):
        valid, invalid = TagVocab(default_vocab()).validate_tags(["python", "unknown-x"])
        assert valid == ["python"]
        assert invalid == ["unknown-x"]

    def test_validate_tags_all_invalid(self):
        valid, invalid = TagVocab(default_vocab()).validate_tags(["nope", "nada"])
        assert valid == []
        assert invalid == ["nope", "nada"]


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


class TestValidatorIntegration:
    def test_valid_tags_from_vocab(self):
        text = json.dumps({"desc": "Helper utilities", "tags": ["python", "lib", "cli"], "signatures": []})
        assert validate_phase_1(text, expected_sig_count=0, vocab=TagVocab(default_vocab())) == []

    def test_invalid_tag_not_in_vocab(self):
        text = json.dumps({"desc": "Helper utilities", "tags": ["python", "INVALID_TAG"], "signatures": []})
        errors = validate_phase_1(text, expected_sig_count=0, vocab=TagVocab(default_vocab()))
        assert any("INVALID_TAG" in error for error in errors)

    def test_new_tag_proposal_accepted(self):
        text = json.dumps({"desc": "Helper utilities", "tags": ["python", "my-new-tag"], "signatures": []})
        assert validate_phase_1(text, expected_sig_count=0, vocab=TagVocab(default_vocab())) == []

    def test_no_vocab_skips_tag_check(self):
        text = json.dumps({"desc": "Helper utilities", "tags": ["anything", "GOES_HERE"], "signatures": []})
        assert validate_phase_1(text, expected_sig_count=0, vocab=None) == []

    def test_mixed_valid_and_invalid_tags(self):
        text = json.dumps({"desc": "ok", "tags": ["python", "Bad Tag!", "cli"], "signatures": []})
        errors = validate_phase_1(text, expected_sig_count=0, vocab=TagVocab(default_vocab()))
        assert len(errors) == 1
        assert "Bad Tag!" in errors[0]
