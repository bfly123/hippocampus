from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install.sh"


def test_install_script_help():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Usage: ./scripts/install.sh" in result.stdout
    assert "hippocampus-llm.yaml" in result.stdout
    assert ".architec/architec-llm.yaml" in result.stdout


def test_install_script_rejects_arguments():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dev"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "takes no arguments" in result.stderr
