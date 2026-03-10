"""LLM-powered architect analysis routines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..config import HippoConfig
from ..llm.client import HippoLLM
from .architect_models import RuleFinding
from .architect_runtime_helpers import run_git_capture


class LLMAnalyzer:
    """LLM-powered deep architecture analysis."""

    def __init__(self, config: HippoConfig):
        self.llm = HippoLLM(config)

    def _summarize_index(self, index: dict) -> str:
        parts = []
        stats = index.get("stats", {})
        project = index.get("project", "unknown")
        parts.append(
            f"Project: {project}\n"
            f"Files: {stats.get('total_files', 0)}, "
            f"Modules: {stats.get('total_modules', 0)}, "
            f"Signatures: {stats.get('total_signatures', 0)}"
        )

        modules = index.get("modules", [])
        parts.append("\n## Modules")
        for module in modules:
            parts.append(
                f"- {module['id']} | tier={module.get('tier','?')} role={module.get('role','?')} "
                f"files={module.get('file_count',0)} core_score={module.get('core_score',0):.3f}"
            )
            desc = module.get("desc", "")
            if desc:
                parts.append(f"  {desc[:120]}")

        mod_deps = index.get("module_dependencies", {})
        parts.append("\n## Module Dependencies")
        for src, deps in mod_deps.items():
            targets = ", ".join(f"{d['target']}(w={d['weight']})" for d in deps)
            parts.append(f"  {src} -> {targets}")

        summary = "\n".join(parts)
        if len(summary) > 8000:
            summary = summary[:7900] + "\n... (truncated)"
        return summary

    def _parse_json_response(self, text: str) -> dict:
        payload = text.strip()
        if "```json" in payload:
            payload = payload.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in payload:
            payload = payload.split("```", 1)[1].split("```", 1)[0].strip()
        return json.loads(payload)

    async def audit(self, index: dict, findings: list[RuleFinding]) -> dict:
        summary = self._summarize_index(index)
        findings_text = (
            "\n".join(
                f"- [{f.severity.value}] {f.rule_id}: {f.message}"
                for f in findings
            )
            or "No rule violations found."
        )

        prompt = f"""You are a senior software architect performing a health audit.

## Architecture Data
{summary}

## Rule Engine Findings
{findings_text}

## Analysis Framework
Apply these principles:
1. **Stable Dependencies Principle (SDP)**: Dependencies should flow toward stability.
   Evaluate whether dependency directions are reasonable.
2. **C4 Model**: Assess health at Component (module) and Code (class/function) levels.

## Output
Return valid JSON only:
{{
    "health_score": <0-100>,
    "summary": "<2-3 sentence overall assessment>",
    "root_causes": ["<root cause 1>", ...],
    "recommendations": [
        {{"priority": "high"|"medium"|"low", "action": "<specific action>"}}
    ],
    "sdp_assessment": "<1-2 sentences on dependency direction health>"
}}"""

        response = await self.llm.call(
            phase="architect",
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_response(response)

    async def review_commits(
        self,
        index: dict,
        findings: list[RuleFinding],
        num_commits: int,
        repo_root: Optional[Path] = None,
    ) -> dict:
        summary = self._summarize_index(index)
        findings_text = (
            "\n".join(
                f"- [{f.severity.value}] {f.rule_id}: {f.message}"
                for f in findings
            )
            or "No rule violations found."
        )

        git_log = run_git_capture(
            ["git", "log", f"-{num_commits}", "--oneline"],
            cwd=repo_root,
        )
        if not git_log.strip():
            raise RuntimeError(
                f"No git history found (requested {num_commits} commits). "
                "Ensure the target is a git repository with sufficient history."
            )
        git_diff = run_git_capture(
            ["git", "diff", f"HEAD~{num_commits}..HEAD", "--stat"],
            cwd=repo_root,
        )
        content_diff = run_git_capture(
            ["git", "diff", f"HEAD~{num_commits}..HEAD"],
            cwd=repo_root,
        )
        if len(content_diff) > 12000:
            content_diff = content_diff[:12000] + "\n... (truncated)"

        prompt = f"""You are a senior software architect reviewing recent commits.

## Architecture Data
{summary}

## Rule Engine Findings (current state)
{findings_text}

## Recent Commits
```
{git_log}
```

## Change Stats
```
{git_diff}
```

## Diff Content
```diff
{content_diff}
```

## Task
Evaluate the architectural impact of these commits. For each commit, assess:
- Does it respect module boundaries?
- Does it introduce new dependencies? Are they in the right direction?
- Does it increase or decrease architectural debt?

## Output
Return valid JSON only:
{{
    "summary": "<overall assessment>",
    "commit_assessments": [
        {{
            "commit": "<hash + message>",
            "impact": "positive"|"neutral"|"negative",
            "notes": "<brief explanation>"
        }}
    ],
    "new_risks": ["<risk if any>"],
    "overall_trend": "improving"|"stable"|"degrading"
}}"""

        response = await self.llm.call(
            phase="architect",
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_response(response)

    async def plan_feature(self, index: dict, description: str) -> dict:
        summary = self._summarize_index(index)
        prompt = f"""You are a senior software architect planning a new feature.

## Architecture Data
{summary}

## Feature Description
{description}

## Task
Determine the best placement for this feature within the existing architecture.
Consider module boundaries, dependency directions, and the Stable Dependencies Principle.

## Output
Return valid JSON only:
{{
    "target_module": "<existing module ID or 'new:suggested-name'>",
    "rationale": "<why this module>",
    "files_to_create": [
        {{"path": "<file path>", "purpose": "<what it does>"}}
    ],
    "files_to_modify": [
        {{"path": "<file path>", "changes": "<what to change>"}}
    ],
    "new_dependencies": [
        {{"from": "<module>", "to": "<module>", "reason": "<why>"}}
    ],
    "risks": ["<risk 1>", ...],
    "impact_blast_radius": ["<existing file that will be affected>", ...],
    "integration_seams": [
        {{"file": "<file path>", "function": "<function name>", "action": "<how to integrate>"}}
    ]
}}"""

        response = await self.llm.call(
            phase="architect",
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_response(response)
