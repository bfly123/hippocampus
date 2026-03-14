# hippocampus

`hippo` is a code repository indexing and navigation toolkit. It builds a local
project map, searchable index, structure prompts, and visualization artifacts
for large codebases.

## What It Does

- Builds `.hippocampus/` artifacts from a repository.
- Generates `hippocampus-index.json`, structure prompts, and HTML visualization.
- Supports incremental refresh with `hippo update`.
- Can emit `architect-metrics.json` for downstream `architec` scoring when
  `architec` is installed.

## Install

### Quick Install

```bash
./install.sh
```

The installer:

- installs `hippocampus` from the current checkout
- installs `llmgateway`, preferring `../llmgateway` and falling back to GitHub
- can generate `~/.hippocampus/hippocampus-llm.yaml`

### Manual Install

```bash
python -m pip install -e ".[dev,repomap,llm]"
```

If you want a ready-to-edit config file:

```bash
cp config/hippocampus-llm.example.yaml ~/.hippocampus/hippocampus-llm.yaml
```

## Quick Start

```bash
hippo --help
hippo onekey --target /path/to/repo
hippo update --target /path/to/repo
hippo overview --target /path/to/repo
```

## Standard Outputs

After `hippo onekey` or `hippo update`, the main artifacts live under
`.hippocampus/`:

- `hippocampus-index.json`
- `code-signatures.json`
- `tree.json`
- `structure-prompt.md`
- `structure-prompt-map.md`
- `structure-prompt-deep.md`
- `hippocampus-viz.html`
- `architect-metrics.json` when `architec` is available

## LLM Configuration

The runtime config file is:

```bash
~/.hippocampus/hippocampus-llm.yaml
```

The simplified format is aligned with `architec` and uses:

- one provider
- one API key
- two model tiers: `strong` and `small`
- visible `max_concurrent` setting

Example:

```yaml
version: 1
settings:
  max_concurrent: 30

providers:
  main:
    base_url: https://your-endpoint.example
    api_key: sk-...

tiers:
  strong:
    candidates:
      - provider: main
        model: gpt-5.4
        reasoning_effort: high
  small:
    candidates:
      - provider: main
        model: gpt-5.4
        reasoning_effort: low
```

## Python API

Stable import-facing APIs are exposed from `hippocampus` and
`hippocampus.api`.

```python
from hippocampus import build_tree, extract_signatures, generate_structure_prompt

extract_signatures("/path/to/repo")
build_tree("/path/to/repo")
generate_structure_prompt("/path/to/repo", profile="map")
```

## Architec Integration

If `architec` is installed, `hippo onekey` and `hippo update` also generate:

```bash
.hippocampus/architect-metrics.json
```

This lets you run architecture scoring directly with `architec`.

## Development

Run a focused local test set with:

```bash
python -m pip install -e ".[dev,repomap,llm]"
pytest -q
```

For installation help:

```bash
./install.sh --help
```

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
