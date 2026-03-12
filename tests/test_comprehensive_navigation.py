"""Comprehensive navigation tests with different token budgets and focus files.

Tests various combinations of:
- Token budgets: 500, 1000, 2500, 5000
- Focus file scenarios: single, multiple, none
- Query types: specific, broad, symbol-focused
"""

import asyncio
import json
from pathlib import Path

import pytest

from hippocampus.config import load_config
from hippocampus.mcp.tools import navigate_tool
from hippocampus.tools.index_gen import run_index_pipeline
from hippocampus.tools.ranker import is_repomap_available


@pytest.fixture
def project_root():
    """Resolve hippocampus project root independent of current working directory."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def hippo_dir(project_root):
    """Use hippocampus-local .hippocampus and rebuild index if fixture data was cleaned."""
    output_dir = project_root / ".hippocampus"
    index_path = output_dir / "hippocampus-index.json"
    rebuild_required = not index_path.is_file()
    if index_path.is_file():
        try:
            index_data = json.loads(index_path.read_text(encoding="utf-8"))
            indexed_files = set(index_data.get("files", {}))
            rebuild_required = (
                "src/hippocampus/tools/index/index_gen.py" not in indexed_files
            )
        except (OSError, json.JSONDecodeError):
            rebuild_required = True

    if rebuild_required:
        cfg = load_config(output_dir / "config.yaml")
        asyncio.run(
            run_index_pipeline(
                target=project_root,
                output_dir=output_dir,
                config=cfg,
                verbose=False,
                no_llm=True,
            )
        )
    return output_dir


# Test scenarios with different focus files
TEST_SCENARIOS = [
    {
        'name': 'Single focus - index gen',
        'query': 'phase_2 process_file cache implementation',
        'focus': ['src/hippocampus/tools/index/index_gen.py'],
        'expected_symbols': ['phase_2', 'process_file'],
        'expected_files': ['src/hippocampus/tools/index/index_gen.py']
    },
    {
        'name': 'Single focus - repomap adapter',
        'query': 'HippoRepoMap get_ranked_tags snippet extraction',
        'focus': ['src/hippocampus/tools/repomap_adapter.py'],
        'expected_symbols': ['HippoRepoMap', 'get_ranked_tags', 'get_ranked_snippets'],
        'expected_files': ['src/hippocampus/tools/repomap_adapter.py']
    },
    {
        'name': 'Multiple focus - tools',
        'query': 'phase_2 and get_ranked_snippets implementation',
        'focus': [
            'src/hippocampus/tools/index/index_gen.py',
            'src/hippocampus/tools/repomap_adapter.py'
        ],
        'expected_symbols': ['phase_2', 'get_ranked_snippets'],
        'expected_files': [
            'src/hippocampus/tools/index/index_gen.py',
            'src/hippocampus/tools/repomap_adapter.py'
        ]
    },
    {
        'name': 'No focus - broad query',
        'query': 'MCP server tool handling',
        'focus': [],
        'expected_symbols': ['handle_tool_call', 'navigate_tool'],
        'expected_files': []  # No specific files required
    },
    {
        'name': 'Single focus - MCP tools',
        'query': 'navigate tool implementation',
        'focus': ['src/hippocampus/mcp/tools.py'],
        'expected_symbols': ['navigate_tool', 'extract_mentions'],
        'expected_files': ['src/hippocampus/mcp/tools.py']
    }
]

TOKEN_BUDGETS = [500, 1000, 2500, 5000]


def _coverage_ratio(found: list[str], expected: list[str]) -> float:
    if not expected:
        return 100.0
    return len(found) / len(expected) * 100


def _snippet_files(result: dict) -> list[str]:
    return [snippet["file"] for snippet in result.get("context_snippets", [])]


def _collect_found_symbols(result: dict) -> list[str]:
    symbols: list[str] = []
    for file_info in result.get("context_snippets", []):
        for snippet in file_info["snippets"]:
            symbols.extend(snippet["symbols"])
    return symbols


def _found_focus_files(snippet_files: list[str], focus_files: list[str]) -> list[str]:
    snippet_files_set = set(snippet_files)
    return [focus_file for focus_file in focus_files if focus_file in snippet_files_set]


def _found_expected_symbols(found_symbols: list[str], expected_symbols: list[str]) -> list[str]:
    found_symbols_lower = {symbol.lower() for symbol in found_symbols}
    return [
        expected_symbol
        for expected_symbol in expected_symbols
        if expected_symbol.lower() in found_symbols_lower
    ]


def _print_scenario_header(scenario) -> None:
    print(f"\n{'='*100}")
    print(f"Scenario: {scenario['name']}")
    print(f"Query: {scenario['query']}")
    print(f"Focus: {scenario['focus']}")
    print(f"{'='*100}")


def _print_budget_metrics(metrics: dict, scenario: dict) -> None:
    print(f"\n  Budget: {metrics['budget']} tokens")
    print(
        f"    Files: {metrics['num_snippet_files']}, "
        f"Snippets: {metrics['num_snippets']}, Tokens: {metrics['total_tokens']}"
    )
    print(
        "    Focus coverage: "
        f"{metrics['focus_coverage']:.0f}% "
        f"({len(metrics['focus_included'])}/{len(scenario['focus']) if scenario['focus'] else 0})"
    )
    print(
        "    Symbol coverage: "
        f"{metrics['symbol_coverage']:.0f}% "
        f"({len(metrics['expected_symbols_found'])}/{len(scenario['expected_symbols'])})"
    )

    if metrics['focus_included']:
        print(f"    ✓ Focus files included: {', '.join(metrics['focus_included'])}")
    elif scenario['focus']:
        missing = sorted(set(scenario['focus']) - set(metrics['focus_included']))
        print(f"    ✗ Missing focus files: {', '.join(missing)}")

    if metrics['expected_symbols_found']:
        print(f"    ✓ Expected symbols found: {', '.join(metrics['expected_symbols_found'])}")


def _assert_navigation_metrics(metrics: dict, scenario: dict, budget: int) -> None:
    if scenario['focus']:
        assert metrics['focus_coverage'] == 100.0, (
            f"Focus coverage must be 100% but got {metrics['focus_coverage']:.0f}%"
        )

    if scenario['expected_symbols'] and budget >= 1000:
        min_coverage = 30.0 if not scenario['focus'] else 50.0
        assert metrics['symbol_coverage'] >= min_coverage, (
            f"Symbol coverage must be >= {min_coverage}% for budget {budget} "
            f"but got {metrics['symbol_coverage']:.0f}%"
        )


def _write_results(all_results: list[dict]) -> Path:
    output_file = Path("/tmp/comprehensive_navigation_results.json")
    output_file.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    return output_file


def _print_summary(all_results: list[dict]) -> None:
    print(f"\n{'='*100}")
    print("SUMMARY STATISTICS")
    print(f"{'='*100}")

    total_tests = len(all_results)
    focus_success = sum(1 for r in all_results if r['focus_coverage'] == 100.0 or not r['focus_files'])
    symbol_success = sum(1 for r in all_results if r['symbol_coverage'] >= 50.0)

    print(f"\nTotal test combinations: {total_tests}")
    print(f"Focus file inclusion: {focus_success}/{total_tests} ({focus_success/total_tests*100:.1f}%)")
    print(f"Good symbol coverage (≥50%): {symbol_success}/{total_tests} ({symbol_success/total_tests*100:.1f}%)")


def _print_scenario_summary(all_results: list[dict]) -> None:
    print(f"\n{'='*100}")
    print("PER-SCENARIO SUMMARY")
    print(f"{'='*100}")

    for scenario in TEST_SCENARIOS:
        scenario_metrics = [r for r in all_results if r['scenario'] == scenario['name']]
        avg_focus = sum(r['focus_coverage'] for r in scenario_metrics) / len(scenario_metrics)
        avg_symbol = sum(r['symbol_coverage'] for r in scenario_metrics) / len(scenario_metrics)
        avg_tokens = sum(r['total_tokens'] for r in scenario_metrics) / len(scenario_metrics)

        print(f"\n{scenario['name']}:")
        print(f"  Avg focus coverage: {avg_focus:.1f}%")
        print(f"  Avg symbol coverage: {avg_symbol:.1f}%")
        print(f"  Avg tokens used: {avg_tokens:.0f}")


def analyze_navigation_result(result, scenario, budget):
    """Analyze a navigation result and return metrics."""
    snippets = result.get("context_snippets", [])
    snippet_files = _snippet_files(result)
    found_symbols = _collect_found_symbols(result)
    focus_included = _found_focus_files(snippet_files, scenario['focus'])
    expected_symbols_found = _found_expected_symbols(found_symbols, scenario['expected_symbols'])

    metrics = {
        'scenario': scenario['name'],
        'budget': budget,
        'query': scenario['query'],
        'focus_files': scenario['focus'],
        'num_snippet_files': len(snippets),
        'num_snippets': sum(len(s['snippets']) for s in snippets),
        'total_tokens': sum(s['total_tokens'] for s in snippets),
        'snippet_files': snippet_files,
        'found_symbols': found_symbols,
        'focus_included': focus_included,
        'expected_symbols_found': expected_symbols_found,
    }
    metrics['focus_coverage'] = _coverage_ratio(metrics['focus_included'], scenario['focus'])
    metrics['symbol_coverage'] = _coverage_ratio(
        metrics['expected_symbols_found'],
        scenario['expected_symbols'],
    )

    return metrics


def test_comprehensive_navigation_matrix(hippo_dir, project_root):
    """Test navigation across all scenarios and token budgets."""
    if not is_repomap_available(project_root):
        pytest.skip("RepoMap not available")

    print("\n" + "="*100)
    print("COMPREHENSIVE NAVIGATION TEST MATRIX")
    print("="*100)

    all_results = []

    for scenario in TEST_SCENARIOS:
        _print_scenario_header(scenario)
        scenario_results = []

        for budget in TOKEN_BUDGETS:
            result = navigate_tool(
                query=scenario['query'],
                focus_files=scenario['focus'],
                budget_tokens=budget,
                hippo_dir=hippo_dir
            )

            metrics = analyze_navigation_result(result, scenario, budget)
            scenario_results.append(metrics)
            all_results.append(metrics)
            _print_budget_metrics(metrics, scenario)
            _assert_navigation_metrics(metrics, scenario, budget)

    output_file = _write_results(all_results)
    print(f"\n📊 Detailed results saved to: {output_file}")
    _print_summary(all_results)
    _print_scenario_summary(all_results)
