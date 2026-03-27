"""File extension to tree-sitter language mapping."""

from __future__ import annotations

# Extension → language name (matching .scm file prefixes)
EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".cs": "c_sharp",
    ".scala": "scala",
    ".sc": "scala",
    ".dart": "dart",
    ".php": "php",
    ".el": "elisp",
    ".ex": "elixir",
    ".exs": "elixir",
    ".elm": "elm",
    ".hs": "haskell",
    ".jl": "julia",
    ".ml": "ocaml",
    ".mli": "ocaml_interface",
    ".ql": "ql",
    ".zig": "zig",
    ".f": "fortran",
    ".f90": "fortran",
    ".f95": "fortran",
    ".f03": "fortran",
    ".for": "fortran",
    ".m": "matlab",
    ".hcl": "hcl",
    ".tf": "hcl",
}


def filename_to_lang(filename: str) -> str | None:
    """Map a filename to its tree-sitter language name.

    Returns None if the language is not supported.
    """
    from pathlib import Path
    suffix = Path(filename).suffix.lower()
    return EXTENSION_MAP.get(suffix)
