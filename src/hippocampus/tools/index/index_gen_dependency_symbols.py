"""Symbol and function dependency helpers for index generation."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

FunctionSpan = tuple[str, int, int]
Reference = tuple[str, int]


def iter_python_functions(tree: ast.AST) -> list[FunctionSpan]:
    functions: list[FunctionSpan] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = node.end_lineno if hasattr(node, "end_lineno") else node.lineno + 50
            functions.append((node.name, node.lineno, end_line))
    return functions


def safe_parse_python_file(full_path: Path, *, filename: str) -> ast.AST | None:
    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
        return ast.parse(content, filename=filename)
    except (SyntaxError, UnicodeDecodeError):
        return None


def collect_symbol_data(
    files_index: dict[str, dict],
    target: Path,
) -> tuple[
    dict[str, list[str]],
    dict[str, list[FunctionSpan]],
    dict[str, list[Reference]],
]:
    from ...constants import HIPPO_DIR, QUERIES_DIR
    from ...nav.extractor import extract_tags_from_file

    symbol_to_files: dict[str, list[str]] = defaultdict(list)
    file_functions: dict[str, list[FunctionSpan]] = defaultdict(list)
    file_references: dict[str, list[Reference]] = defaultdict(list)
    queries_dir = target / HIPPO_DIR / QUERIES_DIR

    for file_path in files_index:
        full_path = target / file_path
        if not full_path.exists():
            continue
        _register_python_symbols(
            file_path,
            full_path,
            file_functions=file_functions,
            symbol_to_files=symbol_to_files,
        )
        try:
            defs, refs = extract_tags_from_file(full_path, target, queries_dir)
        except Exception:
            continue
        _register_extracted_tags(
            file_path,
            defs,
            refs,
            file_functions=file_functions,
            symbol_to_files=symbol_to_files,
            file_references=file_references,
        )

    return symbol_to_files, file_functions, file_references


def _register_python_symbols(
    file_path: str,
    full_path: Path,
    *,
    file_functions: dict[str, list[FunctionSpan]],
    symbol_to_files: dict[str, list[str]],
) -> None:
    if not file_path.endswith(".py"):
        return
    tree = safe_parse_python_file(full_path, filename=file_path)
    if tree is None:
        return
    python_functions = iter_python_functions(tree)
    if not python_functions:
        return
    file_functions[file_path].extend(python_functions)
    for func_name, _start, _end in python_functions:
        symbol_to_files[func_name].append(file_path)


def _register_extracted_tags(
    file_path: str,
    defs,
    refs,
    *,
    file_functions: dict[str, list[FunctionSpan]],
    symbol_to_files: dict[str, list[str]],
    file_references: dict[str, list[Reference]],
) -> None:
    if not file_functions.get(file_path):
        for tag in defs:
            if tag.kind != "def":
                continue
            symbol_to_files[tag.name].append(file_path)
            file_functions[file_path].append((tag.name, tag.line, tag.line + 100))
    for tag in refs:
        if tag.kind == "ref":
            file_references[file_path].append((tag.name, tag.line))


def find_enclosing_function(functions: list[FunctionSpan], *, ref_line: int) -> str | None:
    for func_name, func_start, func_end in functions:
        if func_start <= ref_line <= func_end:
            return func_name
        if func_start > ref_line:
            break
    return None


def iter_function_dependency_edges(
    file_references: dict[str, list[Reference]],
    file_functions: dict[str, list[FunctionSpan]],
    symbol_to_files: dict[str, list[str]],
):
    for source_file, refs in file_references.items():
        source_funcs = sorted(file_functions.get(source_file, []), key=lambda item: item[1])
        if not source_funcs:
            continue
        yield from _iter_file_function_edges(
            source_file,
            refs,
            source_funcs=source_funcs,
            file_functions=file_functions,
            symbol_to_files=symbol_to_files,
        )


def _iter_file_function_edges(
    source_file: str,
    refs: list[Reference],
    *,
    source_funcs: list[FunctionSpan],
    file_functions: dict[str, list[FunctionSpan]],
    symbol_to_files: dict[str, list[str]],
):
    for ref_name, ref_line in refs:
        caller_func = find_enclosing_function(source_funcs, ref_line=ref_line)
        if not caller_func:
            continue
        caller_key = f"{source_file}:{caller_func}"
        for target_file in symbol_to_files.get(ref_name, []):
            callee_key = _callee_key(ref_name, target_file, file_functions)
            if callee_key and caller_key != callee_key:
                yield caller_key, callee_key, ref_line


def _callee_key(
    ref_name: str,
    target_file: str,
    file_functions: dict[str, list[FunctionSpan]],
) -> str | None:
    target_func_names = {
        func_name for func_name, _start, _end in file_functions.get(target_file, [])
    }
    if ref_name not in target_func_names:
        return None
    return f"{target_file}:{ref_name}"
