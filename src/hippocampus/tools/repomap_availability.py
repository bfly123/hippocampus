from __future__ import annotations

from pathlib import Path

from .._vendor.aider_mini import RepoMap

# Delayed RepoMap availability check (avoid import-time side effects)
_repomap_check_cache: dict[str, tuple[bool, str]] = {}


def check_repomap_available(root: Path = None) -> tuple[bool, str]:
    """Check if RepoMap is truly available with all dependencies."""
    global _repomap_check_cache

    if root is None:
        root = Path.cwd()
    root = Path(root).resolve()
    cache_key = str(root)

    if cache_key in _repomap_check_cache:
        return _repomap_check_cache[cache_key]

    try:
        from .tree_sitter_compat import ensure_compatibility

        if not ensure_compatibility():
            raise ImportError("Failed to apply tree-sitter compatibility patch")

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            test_io = type(
                "TestIO",
                (),
                {
                    "read_text": lambda self, f, silent=False: "def test(): pass",
                    "tool_error": lambda self, msg="": None,
                    "tool_warning": lambda self, msg="": None,
                    "tool_output": lambda self, msg="", **kw: None,
                },
            )()
            test_model = type(
                "TestModel",
                (),
                {"token_count": lambda self, text: len(text) // 4},
            )()

            repomap = RepoMap(
                map_tokens=100,
                root=tmpdir,
                main_model=test_model,
                io=test_io,
                verbose=False,
            )

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def test(): pass")
            try:
                list(repomap.get_tags(str(test_file), "test.py"))
            except AttributeError as exc:
                if "captures" in str(exc):
                    raise ImportError(
                        f"tree-sitter API incompatibility: {exc}. "
                        "Compatibility patch may have failed."
                    )
                raise

        result = (True, "")
        _repomap_check_cache[cache_key] = result
        return result
    except ImportError as exc:
        result = (False, f"Import failed: {exc}")
        _repomap_check_cache[cache_key] = result
        return result
    except Exception as exc:
        result = (False, f"Instantiation failed: {exc}")
        _repomap_check_cache[cache_key] = result
        return result


__all__ = ["check_repomap_available"]
