"""LLM-powered architect analysis routines."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...config import HippoConfig
from ...llm.gateway import create_llm_gateway
from ...llm.prompts import (
    build_architect_audit_messages,
    build_architect_plan_messages,
    build_architect_review_messages,
)
from .architect_models import RuleFinding
from .architect_runtime_helpers import run_git_capture


class LLMAnalyzer:
    """LLM-powered deep architecture analysis."""

    def __init__(self, config: HippoConfig):
        self.config = config
        self.llm = create_llm_gateway(config)

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

    async def audit(self, index: dict, findings: list[RuleFinding]) -> dict:
        summary = self._summarize_index(index)
        project_root = Path(self.config.target).resolve()
        findings_text = (
            "\n".join(
                f"- [{f.severity.value}] {f.rule_id}: {f.message}"
                for f in findings
            )
            or "No rule violations found."
        )

        result = await self.llm.run_json_task(
            "architect",
            build_architect_audit_messages(
                project_root=project_root,
                summary=summary,
                findings_text=findings_text,
            ),
        )
        return result.data if isinstance(result.data, dict) else {}

    async def review_commits(
        self,
        index: dict,
        findings: list[RuleFinding],
        num_commits: int,
        repo_root: Optional[Path] = None,
    ) -> dict:
        summary = self._summarize_index(index)
        project_root = repo_root.resolve() if repo_root is not None else Path(self.config.target).resolve()
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

        result = await self.llm.run_json_task(
            "architect",
            build_architect_review_messages(
                project_root=project_root,
                summary=summary,
                findings_text=findings_text,
                git_log=git_log,
                git_diff=git_diff,
                content_diff=content_diff,
            ),
        )
        return result.data if isinstance(result.data, dict) else {}

    async def plan_feature(self, index: dict, description: str) -> dict:
        summary = self._summarize_index(index)
        project_root = Path(self.config.target).resolve()
        result = await self.llm.run_json_task(
            "architect",
            build_architect_plan_messages(
                project_root=project_root,
                summary=summary,
                description=description,
            ),
        )
        return result.data if isinstance(result.data, dict) else {}
