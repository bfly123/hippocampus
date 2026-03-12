"""Tag extraction helpers for embedded RepoMap."""

from __future__ import annotations

import warnings
from collections import namedtuple
from importlib import resources

from grep_ast import filename_to_lang
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token

warnings.simplefilter("ignore", category=FutureWarning)
from grep_ast.tsl import USING_TSL_PACK, get_language, get_parser  # noqa: E402

Tag = namedtuple("Tag", "rel_fname fname line name kind".split())

QUERY_ALIASES = {
    "c_sharp": ("c_sharp", "csharp"),
    "csharp": ("csharp", "c_sharp"),
}


def _iter_query_names(lang: str) -> tuple[str, ...]:
    aliases = QUERY_ALIASES.get(lang)
    if aliases:
        return tuple(f"{name}-tags.scm" for name in aliases)
    return (f"{lang}-tags.scm",)


def load_query_scm(lang: str) -> str | None:
    queries_dir = resources.files("hippocampus").joinpath("resources", "queries")
    for query_name in _iter_query_names(lang):
        query_ref = queries_dir.joinpath(query_name)
        if query_ref.is_file():
            return query_ref.read_text(encoding="utf-8")
    return None


def _capture_nodes(captures) -> list[tuple[object, str]]:
    if USING_TSL_PACK:
        nodes: list[tuple[object, str]] = []
        for tag, capture_nodes in captures.items():
            nodes.extend((node, tag) for node in capture_nodes)
        return nodes
    return list(captures)


def _backfill_refs(fname: str, rel_fname: str, code: str):
    try:
        lexer = guess_lexer_for_filename(fname, code)
    except Exception:
        return

    tokens = [token[1] for token in lexer.get_tokens(code) if token[0] in Token.Name]
    for token in tokens:
        yield Tag(
            rel_fname=rel_fname,
            fname=fname,
            name=token,
            kind="ref",
            line=-1,
        )


def get_tags_raw(repomap, fname: str, rel_fname: str):
    lang = filename_to_lang(fname)
    if not lang:
        return

    try:
        language = get_language(lang)
        parser = get_parser(lang)
    except Exception as err:
        print(f"Skipping file {fname}: {err}")
        return

    query_scm = load_query_scm(lang)
    if not query_scm:
        return

    code = repomap.io.read_text(fname)
    if not code:
        return

    tree = parser.parse(bytes(code, "utf-8"))
    query = language.query(query_scm)
    captures = query.captures(tree.root_node)

    saw: set[str] = set()
    for node, tag in _capture_nodes(captures):
        if tag.startswith("name.definition."):
            kind = "def"
        elif tag.startswith("name.reference."):
            kind = "ref"
        else:
            continue

        saw.add(kind)
        yield Tag(
            rel_fname=rel_fname,
            fname=fname,
            name=node.text.decode("utf-8"),
            kind=kind,
            line=node.start_point[0],
        )

    if "ref" in saw or "def" not in saw:
        return

    yield from _backfill_refs(fname, rel_fname, code)
