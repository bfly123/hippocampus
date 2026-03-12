"""IO tests for hippocampus.tag_vocab."""

from __future__ import annotations

from hippocampus.tag_vocab import TagVocab, default_vocab, load_vocab, save_vocab


class TestVocabIO:
    def test_save_and_load_roundtrip(self, tmp_path):
        vocab = TagVocab(default_vocab())
        vocab.add_tag("extra-one", dimension="custom")
        save_vocab(tmp_path, vocab)

        restored = load_vocab(tmp_path)
        assert restored.contains("python")
        assert restored.contains("extra-one")
        assert vocab.content_hash() == restored.content_hash()

    def test_load_missing_file_returns_default(self, tmp_path):
        vocab = load_vocab(tmp_path)
        default = TagVocab(default_vocab())
        assert vocab.contains("python")
        assert vocab.contains("entrypoint")
        assert vocab.content_hash() == default.content_hash()

    def test_save_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "sub" / "dir"
        save_vocab(nested, TagVocab(default_vocab()))
        assert load_vocab(nested).contains("python")
