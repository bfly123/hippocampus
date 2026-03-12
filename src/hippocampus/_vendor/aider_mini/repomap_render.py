"""Tree rendering helpers for embedded RepoMap."""

from __future__ import annotations

from grep_ast import TreeContext

from .repomap_tags import Tag


def render_tree(repomap, abs_fname, rel_fname, lois):
    mtime = repomap._get_mtime(abs_fname)
    key = (rel_fname, tuple(sorted(lois)), mtime)
    if key in repomap.tree_cache:
        return repomap.tree_cache[key]

    cached_context = repomap.tree_context_cache.get(rel_fname)
    if cached_context is None or cached_context["mtime"] != mtime:
        code = repomap.io.read_text(abs_fname) or ""
        if not code.endswith("\n"):
            code += "\n"
        context = TreeContext(
            rel_fname,
            code,
            color=False,
            line_number=False,
            child_context=False,
            last_line=False,
            margin=0,
            mark_lois=False,
            loi_pad=0,
            show_top_of_file_parent_scope=False,
        )
        repomap.tree_context_cache[rel_fname] = {"context": context, "mtime": mtime}

    context = repomap.tree_context_cache[rel_fname]["context"]
    context.lines_of_interest = set()
    context.add_lines_of_interest(lois)
    context.add_context()
    rendered = context.format()
    repomap.tree_cache[key] = rendered
    return rendered


def to_tree(repomap, tags, chat_rel_fnames):
    if not tags:
        return ""

    current_fname = None
    current_abs_fname = None
    lois = None
    output = ""
    dummy_tag = (None,)

    for tag in sorted(tags) + [dummy_tag]:
        rel_fname = tag[0]
        if rel_fname in chat_rel_fnames:
            continue

        if rel_fname != current_fname:
            if lois is not None:
                output += "\n"
                output += current_fname + ":\n"
                output += render_tree(repomap, current_abs_fname, current_fname, lois)
                lois = None
            elif current_fname:
                output += "\n" + current_fname + "\n"

            if isinstance(tag, Tag):
                lois = []
                current_abs_fname = tag.fname
            current_fname = rel_fname

        if lois is not None:
            lois.append(tag.line)

    return "\n".join(line[:100] for line in output.splitlines()) + "\n"
