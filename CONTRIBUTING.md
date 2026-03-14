# Contributing

## Scope

This repository accepts fixes and improvements for:

- indexing and navigation quality
- CLI usability
- structure prompt generation
- visualization output
- configuration and install flow

## Before Opening A PR

- keep changes focused
- avoid unrelated refactors
- add or update tests for behavior changes
- run the relevant local test subset

## Local Setup

```bash
./install.sh
```

Or manually:

```bash
python -m pip install -e ".[dev,repomap,llm]"
```

## Test

```bash
pytest -q
```

If you are only touching CLI/help/install surfaces, a focused subset is enough.

## Pull Requests

- describe the user-facing effect
- mention changed commands or artifacts when relevant
- include test coverage or explain why tests were not added
