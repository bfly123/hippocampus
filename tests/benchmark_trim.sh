#!/bin/bash
set -e

echo "=== Trim Performance Benchmark ==="

# Test different methods
for method in heuristic graph; do
    echo ""
    echo "Method: $method"
    time python3 -c "from hippocampus.cli import cli; cli(['trim', '--budget', '10000', '--ranking', '$method'])" 2>&1 | grep "Done:"
done

# Test cache effect (second run should be similar)
echo ""
echo "Testing second run (cache effect):"
time python3 -c "from hippocampus.cli import cli; cli(['trim', '--budget', '10000', '--ranking', 'graph'])" 2>&1 | grep "Done:"

# Test different budgets
echo ""
echo "=== Budget Scaling ==="
for budget in 2000 5000 10000 20000; do
    echo ""
    echo "Budget: $budget"
    time python3 -c "from hippocampus.cli import cli; cli(['trim', '--budget', '$budget', '--ranking', 'graph'])" 2>&1 | grep "Done:"
done
