from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..config import HippoConfig
from ..constants import HIPPO_DIR
from ..tag_vocab import TagVocab, is_valid_new_tag, load_vocab, save_vocab
from ..utils import is_doc, is_hidden, is_runtime_artifact
from .index_gen_reporting import format_failed_file_summary
from .index_gen_phase1_runner import run_phase1_processors


async def phase_1_impl(
    config: HippoConfig,
    phase0_data: dict[str, Any],
    target: Path,
    output_dir: Path | None,
    dir_tree: str,
    verbose: bool,
    *,
    content_hash_fn: Callable[[str], str],
    load_phase1_cache_fn: Callable[[Path], dict[str, Any]],
    save_phase1_cache_fn: Callable[[Path, dict[str, Any]], None],
    detect_lang_hint_fn: Callable[[Path], str],
) -> dict[str, dict]:
    from ..llm.client import HippoLLM
    from ..llm.prompts import build_phase_1_messages
    from ..llm.validators import _try_parse_json, validate_phase_1

    llm = HippoLLM(config)
    sig_doc = phase0_data["signatures"]
    compress = phase0_data["compress"]
    files_data = {
        fp: content
        for fp, content in compress.get("files", {}).items()
        if not is_hidden(Path(fp))
        and not is_doc(Path(fp))
        and not is_runtime_artifact(Path(fp))
        and not Path(fp).parts[0] == "vendor"
    }
    lang_hint = detect_lang_hint_fn(target)

    if output_dir is None:
        output_dir = target / HIPPO_DIR
    cache = load_phase1_cache_fn(output_dir)

    vocab = load_vocab(output_dir)
    vocab_hash = vocab.content_hash()

    current_hashes: dict[str, str] = {}
    for fp, content in files_data.items():
        file_sigs = sig_doc.files.get(fp)
        sig_text = ""
        if file_sigs:
            sig_text = "|".join(
                f"{s.name}:{s.kind}:{s.line}" for s in file_sigs.signatures
            )
        current_hashes[fp] = content_hash_fn(content + sig_text + vocab_hash)

    to_process: list[str] = []
    results: dict[str, dict] = {}
    reused = 0
    for fp in files_data:
        h = current_hashes[fp]
        cached = cache.get(fp)
        if cached and cached.get("hash") == h:
            results[fp] = cached["result"]
            reused += 1
        else:
            to_process.append(fp)

    removed = [fp for fp in cache if fp not in files_data]

    if verbose:
        print(
            f"Phase 1 incremental: {reused} cached, "
            f"{len(to_process)} to process, "
            f"{len(removed)} removed"
        )

    failed: list[str] = []

    async def process_file(fpath: str) -> None:
        content = files_data.get(fpath, "")
        file_sigs = sig_doc.files.get(fpath)
        sig_count = len(file_sigs.signatures) if file_sigs else 0
        sig_text = ""
        if file_sigs:
            sig_text = "\n".join(
                f"- {s.name} ({s.kind}, line {s.line})"
                for s in file_sigs.signatures
            )
        lang = file_sigs.lang if file_sigs else "unknown"

        messages = build_phase_1_messages(
            project_root=target,
            file_path=fpath,
            lang=lang,
            dir_tree=dir_tree[:4000],
            compress_content=content[:5000],
            signatures=sig_text or "(none)",
            lang_hint=lang_hint,
            sig_count=sig_count,
            tag_vocab=vocab.format_for_prompt(),
        )

        def validator(text: str) -> list[str]:
            return validate_phase_1(text, sig_count, vocab=vocab)

        text, errors = await llm.call_with_retry("phase_1", messages, validator)
        if errors:
            failed.append(fpath)
            return

        data, _ = _try_parse_json(text)
        if not data:
            return
        _merge_tags_into_vocab(vocab, data.get("tags", []))
        results[fpath] = data
        cache[fpath] = {"hash": current_hashes[fpath], "result": data}

    await run_phase1_processors(
        to_process,
        process_file=process_file,
        verbose=verbose,
    )

    for fp in removed:
        del cache[fp]

    save_phase1_cache_fn(output_dir, cache)
    save_vocab(output_dir, vocab)

    if verbose and failed:
        print(
            format_failed_file_summary(
                failed,
                total_processed=len(to_process),
            )
        )

    return results


def _merge_tags_into_vocab(vocab: TagVocab, tags: list[str]) -> None:
    for tag in tags:
        if not vocab.contains(tag) and is_valid_new_tag(tag):
            vocab.add_tag(tag)
