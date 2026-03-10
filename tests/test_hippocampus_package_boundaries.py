from pathlib import Path


def test_hippocampus_source_does_not_import_cortex_or_llm_proxy():
    root = Path(__file__).resolve().parents[1] / "src" / "hippocampus"
    offenders: list[str] = []

    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from cortex" in text or "import cortex" in text:
            offenders.append(str(path.relative_to(root.parent.parent)))
        if "from llm_proxy" in text or "import llm_proxy" in text:
            offenders.append(str(path.relative_to(root.parent.parent)))

    assert offenders == [], f"hippocampus must stay standalone: {offenders}"


def test_hippocampus_memory_shims_removed():
    repo_root = Path(__file__).resolve().parents[2]
    legacy_paths = [
        repo_root / "hippocampus" / "src" / "hippocampus" / "cli_memory.py",
        repo_root / "hippocampus" / "src" / "hippocampus" / "memory",
    ]
    leftovers = [str(path.relative_to(repo_root)) for path in legacy_paths if path.exists()]
    assert leftovers == [], f"legacy hippocampus memory surfaces must be removed: {leftovers}"
