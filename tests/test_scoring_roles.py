"""Tests for scoring role helpers."""

from __future__ import annotations

from hippocampus.scoring import (
    _classify_file_viz_role,
    _classify_module_role,
    _classify_tier,
    _file_role_bonus,
)


class TestFileRoleBonus:
    def test_entrypoint_tag(self):
        assert _file_role_bonus(["entrypoint", "python"]) == 1.0

    def test_api_tag(self):
        assert _file_role_bonus(["api", "python"]) == 0.8

    def test_test_tag(self):
        assert _file_role_bonus(["test", "python"]) == 0.2

    def test_no_match(self):
        assert _file_role_bonus(["python", "data"]) == 0.0

    def test_first_match_wins(self):
        assert _file_role_bonus(["entrypoint", "test"]) == 1.0


class TestClassifyTier:
    def test_core(self):
        assert _classify_tier(0.35) == "core"
        assert _classify_tier(0.30) == "core"

    def test_secondary(self):
        assert _classify_tier(0.15) == "secondary"
        assert _classify_tier(0.10) == "secondary"

    def test_peripheral(self):
        assert _classify_tier(0.05) == "peripheral"
        assert _classify_tier(0.0) == "peripheral"


class TestClassifyFileVizRoleTestPaths:
    def test_tests_dir(self):
        assert _classify_file_viz_role("tests/test_engine.py", {}) == "test"

    def test_test_prefix(self):
        assert _classify_file_viz_role("test_foo.py", {}) == "test"

    def test_test_suffix(self):
        assert _classify_file_viz_role("engine_test.py", {}) == "test"

    def test_spec_suffix(self):
        assert _classify_file_viz_role("engine_spec.py", {}) == "test"

    def test_conftest(self):
        assert _classify_file_viz_role("tests/conftest.py", {}) == "test"

class TestClassifyFileVizRoleDocsInfraPaths:
    def test_markdown_docs(self):
        assert _classify_file_viz_role("README.md", {}) == "docs"

    def test_docs_dir(self):
        assert _classify_file_viz_role("docs/guide.txt", {}) == "docs"

    def test_license(self):
        assert _classify_file_viz_role("LICENSE", {}) == "docs"

    def test_changelog(self):
        assert _classify_file_viz_role("CHANGELOG.md", {}) == "docs"

    def test_yaml_infra(self):
        assert _classify_file_viz_role("config.yml", {}) == "infra"

    def test_toml_infra(self):
        assert _classify_file_viz_role("pyproject.toml", {}) == "infra"

    def test_setup_py_infra(self):
        assert _classify_file_viz_role("setup.py", {}) == "infra"

    def test_makefile_infra(self):
        assert _classify_file_viz_role("Makefile", {}) == "infra"

    def test_dockerfile_infra(self):
        assert _classify_file_viz_role("Dockerfile", {}) == "infra"

    def test_dotenv_infra(self):
        assert _classify_file_viz_role(".env", {}) == "infra"

class TestClassifyFileVizRoleInterfacePaths:
    def test_cli_dir_interface(self):
        assert _classify_file_viz_role("cli/main.py", {}) == "interface"

    def test_mcp_dir_interface(self):
        assert _classify_file_viz_role("mcp/server.py", {}) == "interface"

    def test_web_dir_interface(self):
        assert _classify_file_viz_role("web/app.py", {}) == "interface"


class TestClassifyFileVizRoleFallbacks:
    def test_tag_test(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["test"]}) == "test"

    def test_tag_entrypoint_interface(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["entrypoint"]}) == "interface"

    def test_tag_config_infra(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["config"]}) == "infra"

    def test_tag_util_infra(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["util"]}) == "infra"

    def test_tag_docs(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["docs"]}) == "docs"

    def test_no_match_defaults_core(self):
        assert _classify_file_viz_role("src/engine.py", {"tags": ["python"]}) == "core"

    def test_path_overrides_tag(self):
        assert _classify_file_viz_role("tests/test_config.py", {"tags": ["config"]}) == "test"


class TestClassifyModuleRole:
    def test_test_files_vote_test(self):
        files = [
            ("tests/test_foo.py", {"tags": ["test", "python"]}),
            ("tests/test_bar.py", {"tags": ["test", "python"]}),
        ]
        assert _classify_module_role("mod:some-tests", files) == "test"

    def test_core_files_vote_core(self):
        files = [
            ("src/engine.py", {"tags": ["lib", "python"]}),
            ("src/parser.py", {"tags": ["core", "python"]}),
        ]
        assert _classify_module_role("mod:engine", files) == "core"

    def test_infra_files_vote_infra(self):
        files = [
            ("setup.py", {"tags": ["config", "python"]}),
            ("config.yml", {"tags": ["util", "python"]}),
        ]
        assert _classify_module_role("mod:utils", files) == "infra"

    def test_md_files_vote_docs(self):
        files = [("README.md", {"tags": []}), ("docs/GUIDE.md", {"tags": []})]
        assert _classify_module_role("mod:documentation", files) == "docs"

    def test_empty_files_default_core(self):
        assert _classify_module_role("mod:empty", []) == "core"

    def test_tiebreak_core_wins(self):
        files = [
            ("src/lib.py", {"tags": ["lib", "python"]}),
            ("setup.cfg", {"tags": ["config", "python"]}),
        ]
        assert _classify_module_role("mod:mixed", files) == "core"

    def test_path_driven_ignores_module_id(self):
        files = [
            ("src/engine.py", {"tags": ["core"]}),
            ("src/parser.py", {"tags": ["lib"]}),
        ]
        assert _classify_module_role("mod:testing", files) == "core"
