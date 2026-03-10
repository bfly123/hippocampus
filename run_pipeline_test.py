"""Sequential pipeline test script with real-time progress."""
import asyncio
import os
import sys
import time
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"
sys.path.insert(0, str(Path(__file__).parent / "src"))

os.environ["ANTHROPIC_API_KEY"] = os.environ.get(
    "ANTHROPIC_API_KEY",
    "sk-ant-oat01-1zXO494m31SWCpVzRd8hEIw73sgTFpppSVAi6K9HX4JdELuqVmqMUwZSM6Yw3h31O-GS4LQQDWFur86iX6zWzXIDBGeHIAA",
)


def log(msg):
    print(msg, flush=True)


TARGET = Path(os.path.expanduser("~/yunwei/claude_codex"))
OUTPUT = TARGET / ".hippocampus"

from hippocampus.config import load_config
from hippocampus.tools.index_gen import (
    phase_0, phase_1, phase_2, phase_3, phase_4_merge,
)
from hippocampus.tools.structure_prompt import _render_node
from hippocampus.types import TreeNode
from hippocampus.utils import read_json, write_json
from hippocampus.constants import TREE_FILE, INDEX_FILE


async def main():
    cfg_path = OUTPUT / "config.yaml"
    cfg = load_config(cfg_path)
    log(f"Config: api_base={cfg.llm.api_base}")
    log(f"Config: max_concurrent={cfg.llm.max_concurrent}")
    log("")

    dir_tree = ""
    tree_path = OUTPUT / TREE_FILE
    if tree_path.exists():
        tree_data = read_json(tree_path)
        root = TreeNode(**tree_data["root"])
        dir_tree = _render_node(root)

    # === Phase 0 ===
    log("=" * 50)
    log("Phase 0: Local extraction (no LLM)")
    log("=" * 50)
    t0 = time.time()
    phase0_data = await phase_0(TARGET, OUTPUT, verbose=True)
    sig_count = len(phase0_data["signatures"].files)
    raw_compress_count = len(phase0_data["compress"].get("files", {}))
    from hippocampus.utils import is_hidden, is_doc
    filtered_compress = {
        fp: c for fp, c in phase0_data["compress"].get("files", {}).items()
        if not is_hidden(Path(fp)) and not is_doc(Path(fp))
    }
    compress_count = len(filtered_compress)
    log(f"  Signatures: {sig_count} files")
    log(f"  Compress: {raw_compress_count} raw -> {compress_count} after filter")
    log(f"  Time: {time.time() - t0:.1f}s")
    log("")

    # === Phase 1 (with per-file progress) ===
    log("=" * 50)
    log(f"Phase 1: Per-file LLM analysis ({compress_count} files, sequential)")
    log("=" * 50)
    t1 = time.time()

    # Monkey-patch phase_1 to add progress logging
    from hippocampus.llm.client import HippoLLM
    from hippocampus.llm.prompts import PHASE_1_SYSTEM, PHASE_1_USER
    from hippocampus.llm.validators import validate_phase_1, _try_parse_json
    from hippocampus.tools.index_gen import _detect_lang_hint

    llm = HippoLLM(cfg)
    sig_doc = phase0_data["signatures"]
    compress = phase0_data["compress"]
    from pathlib import PurePosixPath
    from hippocampus.utils import is_hidden, is_doc
    files_data = {
        fp: content for fp, content in compress.get("files", {}).items()
        if not is_hidden(Path(fp)) and not is_doc(Path(fp))
    }
    lang_hint = _detect_lang_hint(TARGET)
    file_list = list(files_data.keys())
    total = len(file_list)

    phase1_results = {}
    failed = []

    for idx, fpath in enumerate(file_list, 1):
        log(f"  [{idx}/{total}] {fpath}")
        content = files_data.get(fpath, "")
        sig_files = sig_doc.files
        file_sigs = sig_files.get(fpath)
        sig_count_f = len(file_sigs.signatures) if file_sigs else 0
        sig_text = ""
        if file_sigs:
            sig_text = "\n".join(
                f"- {s.name} ({s.kind}, line {s.line})"
                for s in file_sigs.signatures
            )
        lang = file_sigs.lang if file_sigs else "unknown"

        user_msg = PHASE_1_USER.format(
            file_path=fpath,
            lang=lang,
            dir_tree=dir_tree[:4000],
            compress_content=content[:5000],
            signatures=sig_text or "(none)",
            lang_hint=lang_hint,
            sig_count=sig_count_f,
        )
        messages = [
            {"role": "system", "content": PHASE_1_SYSTEM},
            {"role": "user", "content": user_msg},
        ]

        def validator(text, sc=sig_count_f):
            return validate_phase_1(text, sc)

        try:
            text, errors = await llm.call_with_retry("phase_1", messages, validator)
            if errors:
                failed.append(fpath)
                log(f"    FAILED: {errors[:2]}")
                continue
            data, _ = _try_parse_json(text)
            if data:
                phase1_results[fpath] = data
        except Exception as e:
            failed.append(fpath)
            log(f"    ERROR: {type(e).__name__}: {e}")

    log(f"  Results: {len(phase1_results)} files analyzed, {len(failed)} failed")
    log(f"  Time: {time.time() - t1:.1f}s")
    if failed:
        log(f"  Failed files: {failed}")
    log("")

    # === Phase 2 ===
    log("=" * 50)
    log("Phase 2: Module clustering (2a + 2b)")
    log("=" * 50)
    t2 = time.time()
    modules, file_to_module = await phase_2(cfg, phase1_results, verbose=True)
    log(f"  Modules: {len(modules)}")
    log(f"  File assignments: {len(file_to_module)}")
    log(f"  Time: {time.time() - t2:.1f}s")
    log("")

    # === Phase 3 ===
    log("=" * 50)
    log(f"Phase 3: Module descriptions ({len(modules)} modules) + project overview")
    log("=" * 50)
    t3 = time.time()
    enriched_modules, project_node = await phase_3(
        cfg, modules, file_to_module, phase1_results, TARGET, verbose=True,
    )
    log(f"  Enriched modules: {len(enriched_modules)}")
    overview = project_node.get("overview", "")
    log(f"  Project overview: {'yes' if overview else 'no'}")
    log(f"  Time: {time.time() - t3:.1f}s")
    log("")

    # === Phase 4 ===
    log("=" * 50)
    log("Phase 4: Merge index")
    log("=" * 50)
    t4 = time.time()
    index = phase_4_merge(
        phase0_data, phase1_results,
        enriched_modules, file_to_module, project_node,
    )
    out_path = OUTPUT / INDEX_FILE
    write_json(out_path, index)
    stats = index["stats"]
    log(f"  Files: {stats['total_files']}")
    log(f"  Modules: {stats['total_modules']}")
    log(f"  Signatures: {stats['total_signatures']}")
    log(f"  Time: {time.time() - t4:.1f}s")
    log("")

    total_time = time.time() - t0
    log("=" * 50)
    log(f"DONE - Total time: {total_time:.1f}s")
    log(f"Index written to: {out_path}")
    log("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
