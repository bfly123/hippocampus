from __future__ import annotations

from pathlib import Path


def normalized_parts(parts: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(part for part in parts if part)


def split_path(path: str) -> tuple[str, ...]:
    return normalized_parts(tuple(Path(path).as_posix().split("/")))


def infer_entry_reason(
    file_path: str,
    archetype_entry_reasons: dict[str, str],
) -> tuple[str, int]:
    parts = split_path(file_path)
    file_name = parts[-1] if parts else file_path
    if file_name in archetype_entry_reasons:
        return archetype_entry_reasons[file_name], 5
    lower_name = file_name.lower()
    if lower_name in {"main.py", "main.ts", "main.js"}:
        return "main application entry", 4
    if lower_name in {"app.py", "app.ts", "app.js"}:
        return "application bootstrap", 4
    if lower_name in {"server.py", "server.ts", "server.js"}:
        return "server bootstrap", 4
    if lower_name in {"index.ts", "index.js"} and len(parts) <= 2:
        return "package entry surface", 3
    if "cli" in lower_name:
        return "CLI entry point", 3
    return "", 0


def rank_entry_files(
    files: dict[str, dict],
    archetype_entry_reasons: dict[str, str],
) -> list[tuple[str, str, float]]:
    ranked: list[tuple[str, str, float]] = []
    for fp, fd in files.items():
        parts = split_path(fp)
        if not parts:
            continue
        if str(fd.get("role", "")) == "test":
            continue
        file_score = float(fd.get("score") or 0)
        reason, reason_score = infer_entry_reason(fp, archetype_entry_reasons)
        if reason_score <= 0:
            continue
        ranked.append((fp, reason, reason_score * 10 + file_score))
    ranked.sort(key=lambda item: (item[2], item[0]), reverse=True)
    return ranked
