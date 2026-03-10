# Git Hooks for Hippocampus

This document describes the git hooks used in the Hippocampus project for automatic index and visualization updates.

## Post-Commit Hook

The post-commit hook automatically refreshes the hippocampus index and generates visualization after each commit.

### Location

`.git/hooks/post-commit`

### What it does

1. **Runs `hippo index`** - Updates the full index and creates a snapshot
2. **Generates visualization** - Updates `hippocampus-viz.html` with latest data

### Installation

The hook is automatically installed when you run `hippo hooks install`. If you need to manually install it:

```bash
# Copy the hook
cp .git/hooks/post-commit.sample .git/hooks/post-commit

# Make it executable
chmod +x .git/hooks/post-commit
```

### Hook Content

```bash
#!/bin/bash
# Hippocampus post-commit hook
# Automatically refresh hippo index and create snapshot after each commit

# Get the project root (parent of .git)
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

# Get commit info
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B | head -1)

echo ""
echo "🦛 Hippocampus: Auto-refreshing index and creating snapshot..."
echo ""

# Check if .hippocampus directory exists, if not initialize
if [ ! -d ".hippocampus" ]; then
    echo "📦 Initializing hippocampus..."
    python3 -m hippocampus.cli init --target . 2>&1 | grep -v "FutureWarning" || true
    echo ""
fi

# Run hippo index (it automatically creates a snapshot)
echo "📊 Running hippo index..."
echo ""

# Capture output and show it
OUTPUT=$(python3 -m hippocampus.cli index --target . 2>&1 | grep -v "FutureWarning" | grep -v "UserWarning" | grep -v "PydanticSerializationUnexpectedValue")

if [ -n "$OUTPUT" ]; then
    echo "$OUTPUT"
    echo ""
    echo "✅ Index updated and snapshot created"
else
    echo "⚠️  No output from index command (may have skipped due to no changes)"
fi

echo ""

# Generate visualization
echo "📊 Generating visualization..."
if /home/bfly/anaconda3/bin/python3 -c "from hippocampus.viz.generator import generate_viz_html; from pathlib import Path; generate_viz_html(Path('.hippocampus'))" 2>&1 | grep -v "Warning" | grep -v "FutureWarning" | grep -v "UserWarning" | grep -v "PydanticSerializationUnexpectedValue" | grep -v "^$" > /dev/null 2>&1; then
    : # Command succeeded, output was filtered
fi

# Check if viz file was updated (more reliable than exit code)
if [ -f ".hippocampus/hippocampus-viz.html" ]; then
    echo "✅ Visualization updated: .hippocampus/hippocampus-viz.html"
else
    echo "⚠️  Visualization generation failed"
fi

echo ""
echo "🎉 Hippocampus auto-refresh complete!"
echo ""

# Always exit successfully to not block the commit
exit 0
```

### Output Example

```
🦛 Hippocampus: Auto-refreshing index and creating snapshot...

📊 Running hippo index...

Done: 93 files, 14 modules.
Snapshot saved: 20260213T051234_028484Z

✅ Index updated and snapshot created

📊 Generating visualization...
✅ Visualization updated: .hippocampus/hippocampus-viz.html

🎉 Hippocampus auto-refresh complete!
```

### Files Updated Automatically

Every commit triggers updates to:

- `.hippocampus/hippocampus-index.json` - Full index
- `.hippocampus/structure-prompt.md` - Structure overview
- `.hippocampus/tree.json` - Directory tree
- `.hippocampus/snapshots/YYYYMMDDTHHMMSS_*.json` - Snapshot
- `.hippocampus/hippocampus-viz.html` - Interactive visualization

### Disabling the Hook

If you want to temporarily disable the hook:

```bash
# Rename it
mv .git/hooks/post-commit .git/hooks/post-commit.disabled

# Or remove execute permission
chmod -x .git/hooks/post-commit
```

### Troubleshooting

**Hook not running:**
- Check if the file is executable: `ls -la .git/hooks/post-commit`
- Make sure it has the shebang: `#!/bin/bash`

**Visualization generation fails:**
- Ensure you have the viz dependencies installed
- Check that `.hippocampus/hippocampus-index.json` exists
- Run manually: `python3 -c "from hippocampus.viz.generator import generate_viz_html; from pathlib import Path; generate_viz_html(Path('.hippocampus'))"`

**Python path issues:**
- Update the Python path in the hook to match your environment
- Current path: `/home/bfly/anaconda3/bin/python3`
- Change to your Python: `which python3`
