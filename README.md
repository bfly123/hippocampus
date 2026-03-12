# hippocampus

Code repository indexing and navigation toolkit.

## Install

```bash
./install.sh
```

This installs `hippocampus` from the current source checkout into the active
Python environment as an editable package, including the dependencies needed
for tests and repomap support.

## CLI

```bash
hippo --help
hippo init
hippo index --no-llm
```

## Prompt Management

Prompt templates are packaged with `hippocampus` and can be overridden in the
same style as `architec`.

- Project override: `.hippocampus/prompts/<name>.md`
- Legacy project override: `hippocampus/prompts/<name>.md`
- Environment override: `HIPPOCAMPUS_PROMPTS_DIR=/path/to/prompts`

The runtime checks overrides first and then falls back to the packaged prompts
inside the installed wheel.

## Python API

```python
from hippocampus import build_index, initialize_project, navigate
```
