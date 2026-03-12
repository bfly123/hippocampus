"""Automated architecture reviewer for code changes."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..config import HippoConfig
from ..llm.client import HippoLLM

_MAX_DIFF_CHARS = 20000
_STRUCTURE_MAP_PATH = Path(".hippocampus/structure-prompt.md")


def _load_structure_map() -> str:
    if not _STRUCTURE_MAP_PATH.exists():
        return "No architecture map found. Please run 'hippo index' first."
    return _STRUCTURE_MAP_PATH.read_text(encoding="utf-8")


def _truncate_diff(diff: str) -> str:
    if len(diff) <= _MAX_DIFF_CHARS:
        return diff
    return diff[:_MAX_DIFF_CHARS] + "\n... (truncated)"


def _build_review_prompt(structure_map: str, diff: str) -> str:
    issue_format = (
        '{"severity": "CRITICAL" | "WARNING" | "INFO", '
        '"file": "<filename>", '
        '"message": "<concise description>"}'
    )
    return f"""
You are the Architecture Gatekeeper for this project.
Your goal is to prevent architectural decay by blocking commits that violate the project's design principles.

CONTEXT:
Project Architecture (from .hippocampus/structure-prompt.md):
```markdown
{structure_map}
```

TASK:
Review the following STAGED CHANGES against the architecture map.

STAGED CHANGES:
```diff
{diff}
```

EVALUATION CRITERIA:
1. **Layer Violation**: Does Core code (Tier 1) import Peripheral code (Tier 3)?
2. **Module Integrity**: Does the change strictly belong to the module it touches? Or is it "spaghetti code"?
3. **Duplication**: Does it reimplement utils already described in the Architecture Map?
4. **Conflict**: Does it contradict the "Architecture" or "Key Files" descriptions?

OUTPUT FORMAT:
Return valid JSON ONLY. No preamble.
{{
    "score": <0-100 integer>,
    "status": "PASS" | "BLOCK",
    "issues": [
        {issue_format}
    ],
    "summary": "<one sentence summary>"
}}

DECISION LOGIC:
- Score < 80 => BLOCK
- Any CRITICAL issue => BLOCK
- Otherwise => PASS
"""


def _strip_markdown_fences(response_text: str) -> str:
    if "```json" in response_text:
        return response_text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in response_text:
        return response_text.split("```", 1)[1].split("```", 1)[0].strip()
    return response_text


def _print_review_result(result: dict) -> bool:
    score = result.get("score", 0)
    status = result.get("status", "BLOCK")
    summary = result.get("summary", "")
    issues = result.get("issues", [])

    print(f"\nArchitecture Score: {score}/100")
    print(f"Summary: {summary}\n")

    has_critical = False
    for issue in issues:
        severity = issue.get("severity", "INFO")
        icon = "[CRIT]" if severity == "CRITICAL" else "[WARN]" if severity == "WARNING" else "[INFO]"
        print(f"{icon} [{severity}] {issue.get('file', '?')}: {issue.get('message', '')}")
        has_critical = has_critical or severity == "CRITICAL"

    return status == "BLOCK" or score < 80 or has_critical


class Reviewer:
    """Architecture reviewer using LLM."""

    def __init__(self, config: HippoConfig | None = None):
        self.config = config or HippoConfig()
        self.llm = HippoLLM(self.config)

    def _get_staged_diff(self) -> str:
        """Get git diff of staged changes."""
        try:
            result = subprocess.run(
                ["git", "diff", "--staged"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ""

    async def review_staged(self) -> int:
        """Review staged changes. Returns exit code (0=Pass, 1=Fail)."""
        diff = self._get_staged_diff()
        if not diff.strip():
            print("No staged changes to review.")
            return 0

        prompt = _build_review_prompt(_load_structure_map(), _truncate_diff(diff))
        print("Reviewing architecture compliance...")

        try:
            response_text = await self.llm.call(
                phase="review",
                messages=[{"role": "user", "content": prompt}],
            )
            result = json.loads(_strip_markdown_fences(response_text))
        except json.JSONDecodeError:
            print(f"Review failed to parse LLM response. Content:\n{response_text}")
            print("   (Allowing commit due to tool error)")
            return 0
        except Exception as exc:
            print(f"Review tool error: {exc}")
            return 0

        if _print_review_result(result):
            print("\nCommit BLOCKED: Architectural violations detected.")
            print("   To bypass (emergency only): git commit --no-verify")
            return 1

        print("\nCommit PASSED.")
        return 0
