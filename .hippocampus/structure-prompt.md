# Repository Structure

AI-powered codebase analysis tool featuring parsing, indexing, memory management, and LLM integration for search and review.

**Architecture**: Modular, layered architecture.

**Scale**: 96 files, 12 modules, primary language: python

## Project Map

### Runtime Architecture

Modular, layered architecture.

### Workspace Layout

- `docs/`: Documentation and references
- `scripts/`: Developer/CI automation scripts
- `src/`: Primary application/source code
- `tests/`: Automated tests and validation suites

### Entry Points

- `src/hippocampus/mcp/server.py`: Server entry
- `pyproject.toml`: Python project and dependency manifest

### Project Boundaries

- `src/`: 55 source files, 0 tests; entry `src/hippocampus/mcp/server.py`; core `src/hippocampus`
- `scripts/`: 1 source files, 0 tests; entry `n/a`; core `n/a`

### Fast Navigation Path

1. Read `src/hippocampus/mcp/server.py` to understand `src` runtime entry.
2. Expand `src/hippocampus` for core implementation details.

### Core Code Areas

- `src/hippocampus`: ~55 source files

## LLM Navigation Brief

**Summary**: Hippocampus is a modular Python service providing AI-powered codebase analysis via an MCP server. It features memory management, navigation graphing, and LLM integration tools for indexing and reviewing code.

### Suggested Reading Order

1. `src/hippocampus/mcp/server.py`: Entry point for the MCP service, defining the server lifecycle and initialization.
2. `src/hippocampus/mcp/schemas.py`: Defines the input/output contracts and data structures used across the API.
3. `src/hippocampus/mcp/tools.py`: Implements the core tool logic that bridges the MCP interface with internal modules.
4. `src/hippocampus/tools/index_gen.py`: Central unified index generator, likely the primary engine for code analysis.
5. `src/hippocampus/memory/store.py`: Core abstraction for data persistence, critical for understanding how state is managed.
6. `src/hippocampus/nav/graph.py`: Implements dependency graphs and PageRank-based file ranking, key to the navigation feature.

### Architecture Axes

- MCP Interface Layer (Server, Schemas, Tools)
- Analysis & Tooling Layer (Index Gen, Architect, Ranker)
- Memory & Persistence Layer (Store, Ingestor, Refresh)
- Navigation & Context Layer (Graph, Builder, Extractor)
- Visualization Layer (Data Transformer)

### Risk Hotspots

- `src/hippocampus/memory/refresh.py` (State Synchronization): Incremental memory refresh with change detection and rebuild logic is complex and prone to data drift if edge cases are missed.
- `src/hippocampus/nav/context.py` (Resource Management): Token budget allocation and context rendering logic can lead to truncation or performance issues if miscalculated.
- `src/hippocampus/tools/repomap_adapter.py` (Integration Stability): External adapter for Aider RepoMap requires handling security and compatibility edge cases, making it fragile to upstream changes.

## Modules

- **core-config** [peripheral] (score=0.00, 0 files): Core configuration utilities and constants.
- **llm-integration** [peripheral] (score=0.00, 0 files): LLM client & review tools integration module
- **memory-store** [peripheral] (score=0.00, 0 files): In-memory data handling and snapshotting logic
- **parsing-extraction** [peripheral] (score=0.00, 0 files): Tree-sitter-based parsing and code signature extraction utilities.
- **navigation-ranking** [peripheral] (score=0.00, 0 files): Builds navigation graphs, manages context, and ranks files.
- **query-api** [peripheral] (score=0.00, 0 files): Search, diff, expand, and analyze indexed code data.
- **mcp-interface** [peripheral] (score=0.00, 0 files): MCP server, schemas, and external access tools
- **tools-pipelines** [peripheral] (score=0.00, 0 files): Repomix wrapper, index, trim, and adapter tools module
- **visualization** [peripheral] (score=0.00, 0 files): HTML generation for UI visualization data transformation
- **documentation** [peripheral] (score=0.00, 0 files): Project documentation and skill definitions
- ... (+2 more modules)

## Directory Tree

```
./
  pyproject.toml
  run_pipeline_test.py
  docs/
    git-hooks.md
    repomap-integration.md
  scripts/
    demo_pipeline.py
    git-hooks/
      post-commit
      pre-commit
  src/
    hippocampus/
      __init__.py
      cli.py
      config.py
      constants.py
      context_summary.py
      proxy_provider.py
      scoring.py
      tag_vocab.py
      types.py
      utils.py
      llm/
        __init__.py
        client.py
        prompts.py
        validators.py
      mcp/
        __init__.py
        schemas.py
        server.py
        tools.py
      memory/
        __init__.py
        ingestor.py
        refresh.py
        store.py
        types.py
      nav/
        __init__.py
        builder.py
        context.py
        context_pack.py
        conversation.py
        extractor.py
        global_memory.py
        graph.py
      parsers/
        __init__.py
        lang_map.py
        query_loader.py
        ts_extract.py
      query/
        __init__.py
        diff.py
        expand.py
        overview.py
        search.py
        stats.py
      repomix/
        __init__.py
        runner.py
      tools/
        __init__.py
        architect.py
        index_gen.py
        ranker.py
        repomap_adapter.py
        reviewer.py
        sig_extract.py
        snapshot.py
        structure_prompt.py
        tree_diff.py
        ... (+3 more files)
      viz/
        __init__.py
        data_transformer.py
        generator.py
        templates.py
  tests/
    benchmark_trim.sh
    conftest.py
    test_aider_contract.py
    test_cli_integration.py
    test_comprehensive_navigation.py
    test_compression_quality.py
    test_config.py
    test_config_discovery.py
    test_diff.py
    test_incremental_cache.py
    ... (+16 more files)
```

## Key Files

- `src/hippocampus/mcp/server.py`: MCP server implementation for hippocampus tools (6 symbols)
- `src/hippocampus/tools/index_gen.py`: Unified index generator for code analysis (30 symbols)
- `src/hippocampus/tools/architect.py`: Hybrid rule-engine and LLM architecture analysis tool (28 symbols)
- `src/hippocampus/memory/store.py`: Abstract and JSONL-based memory store implementations (14 symbols)
- `src/hippocampus/memory/refresh.py`: Incremental memory refresh with change detection and rebuild logic (13 symbols)
- `src/hippocampus/mcp/schemas.py`: MCP tool input/output schemas for navigation and memory queries (9 symbols)
- `src/hippocampus/nav/conversation.py`: Extracts conversation context for navigation (8 symbols)
- `src/hippocampus/memory/types.py`: Memory system type definitions and data structures (7 symbols)
- `src/hippocampus/memory/ingestor.py`: Extract and ingest memory from docs, configs, code, and sessions (7 symbols)
- `src/hippocampus/nav/context.py`: Token budget allocation and context rendering for navigation (5 symbols)
- `src/hippocampus/tools/ranker.py`: File ranking strategies for prioritizing code files. (16 symbols)
- `src/hippocampus/nav/extractor.py`: Extract code definitions and references using tree-sitter (4 symbols)
- `src/hippocampus/mcp/tools.py`: MCP tool implementations for navigation, memory, and context. (4 symbols)
- `src/hippocampus/viz/data_transformer.py`: Transforms module data for visualization. (15 symbols)
- `src/hippocampus/nav/graph.py`: PageRank-based file ranking using dependency graphs (3 symbols)
- `src/hippocampus/nav/global_memory.py`: Load module scores and compute file-level priors from index (3 symbols)
- `src/hippocampus/tools/repomap_adapter.py`: Aider RepoMap integration adapter with security and compatibility handling (14 symbols)
- `src/hippocampus/nav/context_pack.py`: Context packing utilities for LLM prompt assembly (2 symbols)

### Test Files

- `tests/test_scoring_query.py`: Python tests for scoring and query modules (70 symbols)
- `tests/test_tag_vocab.py`: Unit tests for tag vocabulary system and validation (42 symbols)
- `tests/test_search.py`: Search query module tests with scoring and integration (41 symbols)
- `tests/test_compression_quality.py`: Python test suite for compression quality benchmark (38 symbols)
- `tests/test_stats.py`: Unit tests for index statistics generation and rendering (28 symbols)
- `tests/test_structure_prompt.py`: Unit tests for structure_prompt markdown generation (27 symbols)
- `tests/test_llm_validators.py`: Unit tests for LLM output validators across pipeline phases (27 symbols)
- `tests/test_snapshot.py`: Snapshot archival tests: save, list, load, resolve operations (26 symbols)
- ... (+18 more test files)

## Signatures

- `src/hippocampus/mcp/server.py`: class MCPServer, function __init__, function _handle_navigate, function _handle_memory_query, function _handle_context_pack, function handle_tool_call
- `src/hippocampus/tools/index_gen.py`: function _content_hash, function _detect_lang_hint, function _build_local_phase1_results, function _infer_primary_lang_from_signatures, function phase_0, function _load_phase1_cache, function _save_phase1_cache, function _phase2_input_hash, function _load_phase2_cache, function _save_phase2_cache
- `src/hippocampus/tools/architect.py`: class Severity, class RuleFinding, class ArchitectReport, class RuleEngine, class LLMAnalyzer, function to_dict, function __init__, function run_all, function _rule_layer_violation, function _rule_circular_dependency
- `src/hippocampus/memory/store.py`: class MemoryStore, class JSONLMemoryStore, function add, function get, function query, function delete, function __init__, function _load, function _save, function _save_atomic
- `src/hippocampus/memory/refresh.py`: function compute_file_hash, function is_git_repo, function compute_queries_checksum, function needs_full_rebuild, function collect_source_files, function detect_changes, function load_metadata, function save_metadata, function run_incremental_sig_extract, function full_rebuild_memory
- `src/hippocampus/mcp/schemas.py`: class NavigateInput, class SnippetInfo, class FileSnippets, class RankedFile, class NavigateOutput, class SymbolRefsInput, class MemoryQueryInput, class MemoryUpsertInput, class ContextPackInput
- `src/hippocampus/nav/conversation.py`: function extract_file_mentions, function extract_idents, function __init__, function add_message, function get_context_text, function get_active_files, function reset, class WorkingMemory
- `src/hippocampus/memory/types.py`: class MemoryType, class MemorySubtype, class MemorySource, class MemoryFreshness, class MemoryRecord, function is_stale, function to_dict
- `src/hippocampus/memory/ingestor.py`: function generate_memory_id, function _generate_tags, function ingest_knowledge_from_docs, function _flatten_dict, function ingest_facts_from_config, function ingest_knowledge_from_code, function ingest_conversation_from_session
- `src/hippocampus/nav/context.py`: function allocate_token_budget, function _estimate_file_tokens, function _truncate_content, function select_files_by_tier, function render_context
- `src/hippocampus/tools/ranker.py`: function is_repomap_available, function rank_files, function rank_files, function _compute_score, function __init__, function rank_files, function _build_dependency_graph, function _extract_imports, function _compute_personalization, function __init__
- `src/hippocampus/nav/extractor.py`: class Tag, function extract_tags_from_file, function extract_tags_batch, function extract_tags_cached
- `src/hippocampus/mcp/tools.py`: function extract_mentions, function navigate_tool, function memory_query_tool, function context_pack_tool
- `src/hippocampus/viz/data_transformer.py`: function transform_modules_to_graph, function _get_tier_color, function _get_role_color, function _calculate_ring_positions, function _calculate_role_positions, function _calculate_tiered_positions, function _compute_frame_diff, function transform_files_to_treemap, function convert_node, function transform_modules_to_treemap
