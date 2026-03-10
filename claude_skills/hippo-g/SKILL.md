---
name: hippo-g
description: Inject .hippocampus/structure-prompt.md into the conversation as project context. Use when the user types /hippo-g or needs codebase structure awareness.
metadata:
  short-description: Inject hippocampus structure prompt
---

# Hippo-G (Inject Structure Prompt)

## Overview

Load the pre-generated `structure-prompt.md` from the project's `.hippocampus/` directory and inject it into the conversation. This gives Claude immediate awareness of the project's modules, key files, signatures, and directory layout.

## Prerequisites

The file `.hippocampus/structure-prompt.md` must exist. Generate it first with:

```bash
python3 -c "from hippocampus.cli import cli; cli(['structure-prompt'])"
```

Or via the hippo CLI:

```bash
hippo structure-prompt
```

## Execution (MANDATORY)

```bash
target="$PWD/.hippocampus/structure-prompt.md"
if [[ ! -f "$target" ]]; then
  echo "ERROR: $target not found. Run 'hippo structure-prompt' first."
  exit 0
fi
printf '@%s\n' "$target"
```

## Output Rules

- When the file exists: output only `@<path>` on a single line.
- When the file is missing: output an error message telling the user to generate it first.

## Examples

- `/hippo-g` -> `@/home/bfly/workspace/hippocampus/.hippocampus/structure-prompt.md`
