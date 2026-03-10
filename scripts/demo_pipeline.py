#!/usr/bin/env python3
"""Demo script: run the context lifecycle + trim pipeline on realistic data.

Usage:
    python scripts/demo_pipeline.py                        # trim-only (detailed stats)
    python scripts/demo_pipeline.py --profile aggressive   # aggressive trim
    python scripts/demo_pipeline.py --mode full            # full lifecycle + trim pipeline
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from llm_proxy.ops.context.directive import LifecycleDirective, TrimDirective
from llm_proxy.ops.context.trimmer import trim_resident
from llm_proxy.ops.context.validator import validate
from llm_proxy.server import LifecyclePipeline

# Reuse the realistic conversation builder from the test suite
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
from test_compression_quality import _build_realistic_conversation


def _print_trim_stats(tr) -> None:
    s = tr.stats
    print(f"  applied:                {tr.applied}")
    print(f"  original_tokens:        {s.original_tokens}")
    print(f"  trimmed_tokens:         {s.trimmed_tokens}")
    print(f"  savings_pct:            {s.savings_pct:.1f}%")
    print(f"  messages_removed:       {s.messages_removed}")
    print(f"  messages_hollowed:      {s.messages_hollowed}")
    print(f"  stale_reads_detected:   {s.stale_reads_detected}")
    print(f"  system_reminders_dedup: {s.system_reminders_deduped}")
    vr = validate(tr.messages)
    print(f"  validation_valid:       {vr.valid}")
    print(f"  output_messages:        {len(tr.messages)}")


def run_trim_only(profile: str) -> None:
    """Run trimmer directly on the conversation for detailed stats."""
    conversation = _build_realistic_conversation()
    print(f"Built conversation: {len(conversation)} messages")

    directive = TrimDirective(
        enabled=True,
        profile=profile,
        stale_read_detection=True,
    )
    result = trim_resident(conversation, directive)

    print(f"\n{'='*60}")
    print(f"Mode: trim-only | Profile: {profile}")
    print(f"{'='*60}")
    print("\n--- Trim Stats ---")
    _print_trim_stats(result)


async def run_full(profile: str) -> None:
    """Run full lifecycle + trim pipeline."""
    conversation = _build_realistic_conversation()
    print(f"Built conversation: {len(conversation)} messages")

    with tempfile.TemporaryDirectory(prefix="demo_pipeline_") as tmpdir:
        db_path = str(Path(tmpdir) / "demo.db")

        pipeline = LifecyclePipeline(
            lifecycle_directive=LifecycleDirective(
                enabled=True,
                high_water=15000,
                target=12000,
                low_water=10000,
                headroom=2000,
            ),
            trim_directive=TrimDirective(
                enabled=True,
                profile=profile,
                stale_read_detection=True,
            ),
            store_path=db_path,
        )

        try:
            body = {"model": "claude-sonnet-4", "messages": conversation}
            result = await pipeline.process(body)

            print(f"\n{'='*60}")
            print(f"Mode: full | Profile: {profile}")
            print(f"Elapsed: {result.elapsed_ms:.1f} ms")
            print(f"{'='*60}")

            print("\n--- Operation Stats ---")
            for op_name, stats in result.operation_stats.items():
                print(f"  [{op_name}]")
                for k, v in stats.items():
                    print(f"    {k}: {v}")

            if result.lifecycle_stats:
                ls = result.lifecycle_stats
                print("\n--- Lifecycle Stats ---")
                print(f"  degraded:        {ls.degraded}")
                print(f"  resident_tokens: {ls.resident_tokens}")
                print(f"  evicted_count:   {ls.evicted_count}")
                print(f"  loaded_count:    {ls.loaded_count}")

            print("\n--- Response Headers ---")
            for k, v in sorted(result.response_headers.items()):
                print(f"  {k}: {v}")
        finally:
            await pipeline.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo context pipeline")
    parser.add_argument(
        "--profile",
        choices=["conservative", "moderate", "aggressive"],
        default="moderate",
    )
    parser.add_argument(
        "--mode",
        choices=["trim", "full"],
        default="trim",
        help="trim = trimmer only (detailed stats), full = lifecycle + trim",
    )
    args = parser.parse_args()
    if args.mode == "full":
        asyncio.run(run_full(args.profile))
    else:
        run_trim_only(args.profile)


if __name__ == "__main__":
    main()
