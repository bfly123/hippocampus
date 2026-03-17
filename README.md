# hippocampus

`hippo` is a code repository indexing and navigation toolkit. It builds a local
project map, searchable index, structure prompts, and visualization artifacts
for large codebases.

## What It Does

- Builds `.hippocampus/` artifacts from a repository.
- Generates `hippocampus-index.json`, structure prompts, and HTML visualization.
- Supports incremental refresh with `hippo update`.
- Can emit `architect-metrics.json` for downstream `archi` scoring when
  `architec` is installed.

## Install

### Quick Install

```bash
./install.sh
```

The installer:

- installs `hippocampus` from the current checkout
- installs `llmgateway`, preferring `../llmgateway` and falling back to GitHub
- can generate `~/.llmgateway/config.yaml`
- can generate `~/.hippocampus/config.yaml`

### Manual Install

```bash
python -m pip install -e ".[dev,repomap,llm]"
```

## Quick Start

```bash
hippo --help
hippo .
hippo /path/to/repo
hippo update --target /path/to/repo
hippo overview --target /path/to/repo
```

## Standard Outputs

After `hippo .` or `hippo update`, the main artifacts live under
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

The runtime config files are:

```bash
~/.llmgateway/config.yaml
~/.hippocampus/config.yaml
```

Responsibilities are split:

- `~/.llmgateway/config.yaml`: provider, API key, base URL, concurrency, strong/weak model selection
- `~/.hippocampus/config.yaml`: Hippo phase-to-tier mapping only

Minimal examples:

```yaml
# ~/.llmgateway/config.yaml
version: 1
settings:
  strong_model: gpt-5.4
  weak_model: gpt-5.4
  strong_reasoning_effort: high
  weak_reasoning_effort: low
  max_concurrent: 30
provider:
  provider_type: glm
  api_style: openai_responses
  base_url: https://your-endpoint.example
  api_key: sk-...
```

```yaml
# ~/.hippocampus/config.yaml
version: 1
tasks:
  phase_1:
    tier: weak
  phase_2a:
    tier: strong
  phase_2b:
    tier: weak
  phase_3a:
    tier: weak
  phase_3b:
    tier: strong
  architect:
    tier: strong
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

If `architec` is installed, `hippo .` and `hippo update` also generate:

```bash
.hippocampus/architect-metrics.json
```

This lets you run architecture scoring directly with `archi`.

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
