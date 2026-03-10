from pathlib import Path

from hippocampus.resources import copy_packaged_queries, packaged_queries_dir


def test_packaged_queries_dir_contains_scm_files():
    with packaged_queries_dir() as queries_dir:
        assert queries_dir.is_dir()
        assert any(queries_dir.glob("*.scm"))


def test_copy_packaged_queries(tmp_path: Path):
    dst = tmp_path / ".hippocampus" / "queries"
    copied = copy_packaged_queries(dst)
    assert copied > 0
    assert any(dst.glob("*.scm"))
