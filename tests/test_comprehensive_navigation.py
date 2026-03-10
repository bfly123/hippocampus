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
    if not (output_dir / "hippocampus-index.json").is_file():
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
        'focus': ['src/hippocampus/tools/index_gen.py'],
        'expected_symbols': ['phase_2', 'process_file'],
        'expected_files': ['src/hippocampus/tools/index_gen.py']
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
            'src/hippocampus/tools/index_gen.py',
            'src/hippocampus/tools/repomap_adapter.py'
        ],
        'expected_symbols': ['phase_2', 'get_ranked_snippets'],
        'expected_files': [
            'src/hippocampus/tools/index_gen.py',
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


def analyze_navigation_result(result, scenario, budget):
    """Analyze a navigation result and return metrics."""
    snippets = result.get("context_snippets", [])

    metrics = {
        'scenario': scenario['name'],
        'budget': budget,
        'query': scenario['query'],
        'focus_files': scenario['focus'],
        'num_snippet_files': len(snippets),
        'num_snippets': sum(len(s['snippets']) for s in snippets),
        'total_tokens': sum(s['total_tokens'] for s in snippets),
        'snippet_files': [s['file'] for s in snippets],
        'found_symbols': [],
        'focus_included': [],
        'expected_symbols_found': [],
    }

    # Collect all found symbols
    for file_info in snippets:
        for snippet in file_info['snippets']:
            metrics['found_symbols'].extend(snippet['symbols'])

    # Check focus file inclusion
    snippet_files_set = set(metrics['snippet_files'])
    for focus_file in scenario['focus']:
        if focus_file in snippet_files_set:
            metrics['focus_included'].append(focus_file)

    # Check expected symbol coverage
    found_symbols_lower = {s.lower() for s in metrics['found_symbols']}
    for expected_symbol in scenario['expected_symbols']:
        if expected_symbol.lower() in found_symbols_lower:
            metrics['expected_symbols_found'].append(expected_symbol)

    # Calculate coverage percentages
    if scenario['focus']:
        metrics['focus_coverage'] = len(metrics['focus_included']) / len(scenario['focus']) * 100
    else:
        metrics['focus_coverage'] = 100.0  # N/A

    if scenario['expected_symbols']:
        metrics['symbol_coverage'] = len(metrics['expected_symbols_found']) / len(scenario['expected_symbols']) * 100
    else:
        metrics['symbol_coverage'] = 100.0  # N/A

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
        print(f"\n{'='*100}")
        print(f"Scenario: {scenario['name']}")
        print(f"Query: {scenario['query']}")
        print(f"Focus: {scenario['focus']}")
        print(f"{'='*100}")

        scenario_results = []

        for budget in TOKEN_BUDGETS:
            # Run navigation with custom budget
            result = navigate_tool(
                query=scenario['query'],
                focus_files=scenario['focus'],
                budget_tokens=budget,
                hippo_dir=hippo_dir
            )

            metrics = analyze_navigation_result(result, scenario, budget)
            scenario_results.append(metrics)
            all_results.append(metrics)

            # Print summary for this budget
            print(f"\n  Budget: {budget} tokens")
            print(f"    Files: {metrics['num_snippet_files']}, Snippets: {metrics['num_snippets']}, Tokens: {metrics['total_tokens']}")
            print(f"    Focus coverage: {metrics['focus_coverage']:.0f}% ({len(metrics['focus_included'])}/{len(scenario['focus']) if scenario['focus'] else 0})")
            print(f"    Symbol coverage: {metrics['symbol_coverage']:.0f}% ({len(metrics['expected_symbols_found'])}/{len(scenario['expected_symbols'])})")

            if metrics['focus_included']:
                print(f"    ✓ Focus files included: {', '.join(metrics['focus_included'])}")
            elif scenario['focus']:
                print(f"    ✗ Missing focus files: {', '.join(set(scenario['focus']) - set(metrics['focus_included']))}")

            if metrics['expected_symbols_found']:
                print(f"    ✓ Expected symbols found: {', '.join(metrics['expected_symbols_found'])}")

            # Critical assertions
            if scenario['focus']:
                # All focus files must be included
                assert metrics['focus_coverage'] == 100.0, \
                    f"Focus coverage must be 100% but got {metrics['focus_coverage']:.0f}%"

            # Symbol coverage assertions - only for larger budgets
            # Small budgets (500) may not capture all symbols
            if scenario['expected_symbols'] and budget >= 1000:
                min_coverage = 30.0 if not scenario['focus'] else 50.0
                assert metrics['symbol_coverage'] >= min_coverage, \
                    f"Symbol coverage must be >= {min_coverage}% for budget {budget} but got {metrics['symbol_coverage']:.0f}%"

    # Save detailed results
    output_file = Path("/tmp/comprehensive_navigation_results.json")
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n📊 Detailed results saved to: {output_file}")

    # Summary statistics
    print(f"\n{'='*100}")
    print("SUMMARY STATISTICS")
    print(f"{'='*100}")

    total_tests = len(all_results)
    focus_success = sum(1 for r in all_results if r['focus_coverage'] == 100.0 or not r['focus_files'])
    symbol_success = sum(1 for r in all_results if r['symbol_coverage'] >= 50.0)

    print(f"\nTotal test combinations: {total_tests}")
    print(f"Focus file inclusion: {focus_success}/{total_tests} ({focus_success/total_tests*100:.1f}%)")
    print(f"Good symbol coverage (≥50%): {symbol_success}/{total_tests} ({symbol_success/total_tests*100:.1f}%)")

    # Group by scenario
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
