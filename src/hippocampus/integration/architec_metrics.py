from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..constants import ARCHITECT_METRICS_FILE, HIPPO_DIR


class ArchitecMetricsError(RuntimeError):
    """Raised when architec metrics generation is available but fails."""


class ArchitecMetricsUnavailable(ArchitecMetricsError):
    """Raised when architec tooling is not installed in the environment."""


@dataclass(frozen=True)
class ArchitecMetricsStatus:
    output_path: Path
    generated: bool
    skipped_reason: str | None = None
    stdout: str = ""
    stderr: str = ""


def _resolve_architec_tooling(project_root: Path) -> tuple[Path, Path]:
    try:
        from architec.integration.resource_paths import resolve_config_file, tool_script_path
    except ModuleNotFoundError as exc:
        raise ArchitecMetricsUnavailable(
            "architec 未安装，跳过 architect-metrics.json 生成。"
        ) from exc

    script_path = Path(tool_script_path("collect_repo_metrics.py")).resolve()
    rubric_path = Path(resolve_config_file(project_root, "rubric.json")).resolve()

    if not script_path.exists():
        raise ArchitecMetricsError(
            f"architec metrics 脚本不存在: {script_path}"
        )
    if not rubric_path.exists():
        raise ArchitecMetricsError(
            f"architec rubric 配置不存在: {rubric_path}"
        )
    return script_path, rubric_path


def generate_architec_metrics_artifact(project_root: str | Path) -> ArchitecMetricsStatus:
    root = Path(project_root).resolve()
    output_path = root / HIPPO_DIR / ARCHITECT_METRICS_FILE
    try:
        script_path, rubric_path = _resolve_architec_tooling(root)
    except ArchitecMetricsUnavailable as exc:
        return ArchitecMetricsStatus(
            output_path=output_path,
            generated=False,
            skipped_reason=str(exc),
        )

    cmd = [
        sys.executable,
        str(script_path),
        "--root",
        str(root),
        "--rubric",
        str(rubric_path),
        "--out",
        str(output_path),
    ]
    result = subprocess.run(
        cmd,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ArchitecMetricsError(
            "architec metrics 生成失败: "
            f"{detail or f'command exited with {result.returncode}'}"
        )
    return ArchitecMetricsStatus(
        output_path=output_path,
        generated=True,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
    )


__all__ = [
    "ArchitecMetricsError",
    "ArchitecMetricsStatus",
    "ArchitecMetricsUnavailable",
    "generate_architec_metrics_artifact",
]
