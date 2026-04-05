"""File extension to tree-sitter language mapping."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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

_DOC_STEMS = frozenset(
    {
        "readme",
        "changelog",
        "changes",
        "license",
        "licence",
        "authors",
        "contributors",
        "copying",
        "notice",
    }
)
_KNOWN_EXTENSIONLESS_SOURCE_NAMES = frozenset(
    {
        "makefile",
        "dockerfile",
        "justfile",
        "jenkinsfile",
        "rakefile",
        "gemfile",
        "vagrantfile",
        "brewfile",
    }
)
_TEXT_PROBE_BYTES = 4096
_SHEBANG_LANGUAGE_MAP = {
    "python": "python",
    "python2": "python",
    "python3": "python",
    "python3.11": "python",
    "node": "javascript",
    "nodejs": "javascript",
    "deno": "javascript",
    "bun": "javascript",
    "ruby": "ruby",
    "php": "php",
}
_SHEBANG_SOURCE_NAMES = frozenset(
    {
        *tuple(_SHEBANG_LANGUAGE_MAP.keys()),
        "sh",
        "bash",
        "zsh",
        "fish",
        "ksh",
        "dash",
        "ash",
        "perl",
    }
)


@dataclass(frozen=True)
class FileLanguageProbe:
    language: str | None
    is_code: bool


def _normalize_stem(name: str) -> str:
    stem = Path(name).stem or Path(name).name
    return "".join(ch for ch in stem.lower() if ch.isalnum())


def _is_doc_name(name: str) -> bool:
    stem = _normalize_stem(name)
    return any(stem.startswith(token) for token in _DOC_STEMS)


def _candidate_interpreters(shebang_line: str) -> list[str]:
    body = shebang_line[2:].strip()
    if not body:
        return []
    tokens = [token for token in body.split() if token]
    if not tokens:
        return []
    first = Path(tokens[0]).name.lower()
    if first != "env":
        return [first]
    out: list[str] = []
    for token in tokens[1:]:
        lowered = Path(token).name.lower()
        if lowered.startswith("-"):
            continue
        out.append(lowered)
    return out


def _probe_from_shebang(text: str) -> FileLanguageProbe | None:
    if not text.startswith("#!"):
        return None
    first_line = text.splitlines()[0] if text.splitlines() else text
    for interpreter in _candidate_interpreters(first_line):
        if interpreter in _SHEBANG_LANGUAGE_MAP:
            return FileLanguageProbe(language=_SHEBANG_LANGUAGE_MAP[interpreter], is_code=True)
        if interpreter in _SHEBANG_SOURCE_NAMES or interpreter.startswith("python"):
            language = "python" if interpreter.startswith("python") else None
            return FileLanguageProbe(language=language, is_code=True)
    return None


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _probe_from_content(text: str) -> FileLanguageProbe:
    sample = _nonempty_lines(text)[:40]
    if not sample:
        return FileLanguageProbe(language=None, is_code=False)

    joined_head = "\n".join(sample[:12])
    if "<?php" in joined_head:
        return FileLanguageProbe(language="php", is_code=True)

    py_score = 0
    js_score = 0
    ruby_score = 0
    for line in sample:
        if line.startswith(("import ", "from ", "def ", "class ", "async def ")):
            py_score += 2
        if line.startswith(("@", "return ", "raise ", "yield ")):
            py_score += 1
        if line.startswith(("if ", "elif ", "else:", "for ", "while ", "with ", "try:", "except ", "finally:", "match ", "case ")):
            py_score += 1
        if "__main__" in line:
            py_score += 3

        if line.startswith(("import ", "export ", "const ", "let ", "var ", "function ")):
            js_score += 2
        if "=>" in line or "require(" in line or "module.exports" in line:
            js_score += 1

        if line.startswith(("require ", "def ", "class ", "module ")):
            ruby_score += 2
        if line in {"end", "begin"} or line.startswith("attr_"):
            ruby_score += 1

    if py_score >= 3:
        return FileLanguageProbe(language="python", is_code=True)
    if js_score >= 3:
        return FileLanguageProbe(language="javascript", is_code=True)
    if ruby_score >= 3:
        return FileLanguageProbe(language="ruby", is_code=True)
    return FileLanguageProbe(language=None, is_code=False)


def _probe_extensionless_file(path: Path) -> FileLanguageProbe:
    name = path.name.lower()
    if _is_doc_name(name):
        return FileLanguageProbe(language=None, is_code=False)
    if name in _KNOWN_EXTENSIONLESS_SOURCE_NAMES:
        return FileLanguageProbe(language=None, is_code=True)
    try:
        with path.open("rb") as handle:
            data = handle.read(_TEXT_PROBE_BYTES)
    except OSError:
        return FileLanguageProbe(language=None, is_code=False)
    if not data or b"\0" in data:
        return FileLanguageProbe(language=None, is_code=False)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return FileLanguageProbe(language=None, is_code=False)
    shebang_probe = _probe_from_shebang(text)
    if shebang_probe is not None:
        return shebang_probe
    return _probe_from_content(text)


def probe_file_language(
    filename: str | Path,
    *,
    project_root: Path | None = None,
) -> FileLanguageProbe:
    """Probe whether a path is code and infer a language when possible."""
    path = Path(filename)
    suffix = path.suffix.lower()
    if suffix:
        language = EXTENSION_MAP.get(suffix)
        return FileLanguageProbe(language=language, is_code=language is not None)
    if _is_doc_name(path.name):
        return FileLanguageProbe(language=None, is_code=False)
    if path.name.lower() in _KNOWN_EXTENSIONLESS_SOURCE_NAMES:
        return FileLanguageProbe(language=None, is_code=True)
    probe_path = path if path.is_absolute() else (project_root / path if project_root is not None else None)
    if probe_path is None or not probe_path.is_file():
        return FileLanguageProbe(language=None, is_code=False)
    return _probe_extensionless_file(probe_path)


def detect_file_language(
    filename: str | Path,
    *,
    project_root: Path | None = None,
) -> str | None:
    """Infer language using extension first and a light probe for extensionless files."""
    return probe_file_language(filename, project_root=project_root).language


def is_probable_source_path(
    filename: str | Path,
    *,
    project_root: Path | None = None,
) -> bool:
    """Return True when the file should be treated as source for architecture indexing."""
    return probe_file_language(filename, project_root=project_root).is_code


def filename_to_lang(filename: str) -> str | None:
    """Map a filename to its tree-sitter language name.

    Returns None if the language is not supported.
    """
    suffix = Path(filename).suffix.lower()
    return EXTENSION_MAP.get(suffix)
