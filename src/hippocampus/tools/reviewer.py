"""Automated architecture reviewer for code changes."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import HippoConfig
from ..llm.client import HippoLLM


class Reviewer:
    """Architecture reviewer using LLM."""

    def __init__(self, config: Optional[HippoConfig] = None):
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

    def _load_structure_map(self) -> str:
        """Load the architecture map."""
        path = Path(".hippocampus/structure-prompt.md")
        if not path.exists():
            return "No architecture map found. Please run 'hippo index' first."
        return path.read_text(encoding="utf-8")

    async def review_staged(self) -> int:
        """Review staged changes. Returns exit code (0=Pass, 1=Fail)."""
        diff = self._get_staged_diff()
        if not diff.strip():
            print("✅ No staged changes to review.")
            return 0

        # Truncate diff if too large (naive truncation)
        # TODO: Use proper token estimation
        if len(diff) > 20000:
            diff = diff[:20000] + "
... (truncated)"

        structure_map = self._load_structure_map()

        prompt = f"""
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
        {{"severity": "CRITICAL" | "WARNING" | "INFO", "file": "<filename>", "message": "<concise description>"}}
    ],
    "summary": "<one sentence summary>"
}}

DECISION LOGIC:
- Score < 80 => BLOCK
- Any CRITICAL issue => BLOCK
- Otherwise => PASS
"""
        print("🔍  Hippocampus: Reviewing architecture compliance...")

        try:
            # We treat this as 'phase 1' or 'structure' prompt type for config purposes
            # reusing an existing phase name if needed, or default
            response_text = await self.llm.call(
                phase="review",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Clean up potential markdown code blocks in response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)
            
            score = result.get("score", 0)
            status = result.get("status", "BLOCK")
            summary = result.get("summary", "")
            issues = result.get("issues", [])

            print(f"
🛡️  Architecture Score: {score}/100")
            print(f"📝 Summary: {summary}
")

            has_critical = False
            for issue in issues:
                sev = issue.get("severity", "INFO")
                icon = "🔴" if sev == "CRITICAL" else "⚠️ " if sev == "WARNING" else "ℹ️ "
                print(f"{icon} [{sev}] {issue.get('file', '?')}: {issue.get('message', '')}")
                if sev == "CRITICAL":
                    has_critical = True

            if status == "BLOCK" or (score < 80) or has_critical:
                print("
❌ Commit BLOCKED: Architectural violations detected.")
                print("   To bypass (emergency only): git commit --no-verify")
                return 1
            
            print("
✅ Commit PASSED.")
            return 0

        except json.JSONDecodeError:
            print(f"⚠️  Review failed to parse LLM response. Content:
{response_text}")
            # Fail safe: warning but allow commit? Or block? 
            # Usually better to block if we promised a gatekeeper, 
            # but for alpha tools, maybe allow with warning.
            print("   (Allowing commit due to tool error)")
            return 0
        except Exception as e:
            print(f"⚠️  Review tool error: {e}")
            return 0
