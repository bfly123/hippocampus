# Hippocampus Phase 1: Reference Implementation Analysis

## Executive Summary

This document contains findings from analyzing three key open-source projects that will inform the Hippocampus code intelligence system implementation:

1. **Repomix** - Code compression and snapshot generation
2. **Aider** - Repository mapping with PageRank-based file ranking
3. **Tree-sitter** - Multi-language code parsing

## Installation Status

### Completed ✅
- **Repomix**: v1.11.1 (npm global install)
- **Tree-sitter**: v0.25.2 (pip install)
- **Tree-sitter-languages**: v1.10.2 (pip install)
- **NetworkX**: v3.1 (already installed)

### In Progress ⏳
- **ChromaDB**: Installation in progress (large dependency tree)
- **Aider**: Cloned but not installed (will analyze code directly)

### Repository Clones ✅
All reference repositories successfully cloned to `vendor/`:
- `vendor/repomix/` - TypeScript/Node.js project
- `vendor/aider/` - Python project
- `vendor/py-tree-sitter/` - Python bindings for tree-sitter

## 1. Aider Repo-Map Analysis

### Location
`vendor/aider/aider/repomap.py` - Main implementation file

### Key Findings

#### Architecture Overview
Aider's repo-map uses a **graph-based approach with PageRank** to rank file importance:

1. **Symbol Extraction** (Tree-sitter based)
   - Extracts definitions (`def`) and references (`ref`) from code
   - Uses `grep-ast` library (wrapper around tree-sitter)
   - Caches parsed tags in `.aider.tags.cache.v{VERSION}/`

2. **Graph Construction** (NetworkX MultiDiGraph)
   - Nodes: Files in the repository
   - Edges: Symbol references between files
   - Edge weights: Based on multiple factors (see below)

3. **PageRank Calculation**
   - Uses NetworkX's `pagerank()` algorithm
   - Personalization vector for files in current context
   - Distributes rank across outgoing edges

4. **Output Generation**
   - Ranked list of file definitions
   - Token-budget aware (fits within LLM context limits)
   - Prioritizes files most relevant to current task

#### Edge Weight Calculation

The weight of an edge from `referencer` → `definer` is calculated as:

```python
weight = mul * sqrt(num_refs)

where mul is determined by:
- Base: 1.0
- × 10 if identifier is in mentioned_idents (from chat)
- × 10 if identifier is well-named (snake_case/kebab-case/camelCase, ≥8 chars)
- × 0.1 if identifier starts with underscore (private)
- × 0.1 if identifier has >5 definitions (too common)
- × 50 if referencer is in chat_fnames (current context)
```

Key insight: `sqrt(num_refs)` prevents high-frequency references from dominating.

#### Personalization Strategy

Files get personalization scores based on:
1. **Chat files**: Files currently being edited (+personalize)
2. **Mentioned files**: Files mentioned in conversation (+personalize)
3. **Path component matching**: If any path component matches a mentioned identifier (+personalize)

```python
personalize = 100 / len(fnames)  # Normalized by repo size
```

#### Caching Strategy

- **Tags cache**: Disk-based cache using `diskcache` library
- **Cache key**: File path + modification time
- **Cache version**: Incremented when tree-sitter changes
- **Error handling**: Graceful degradation on SQLite errors

### Code Snippets

**Graph construction** (lines 451-495):
```python
G = nx.MultiDiGraph()

# Build edges based on symbol references
for ident in idents:
    definers = defines[ident]
    mul = 1.0

    # Weight adjustments
    is_snake = ("_" in ident) and any(c.isalpha() for c in ident)
    is_kebab = ("-" in ident) and any(c.isalpha() for c in ident)
    is_camel = any(c.isupper() for c in ident) and any(c.islower() for c in ident)

    if ident in mentioned_idents:
        mul *= 10
    if (is_snake or is_kebab or is_camel) and len(ident) >= 8:
        mul *= 10
    if ident.startswith("_"):
        mul *= 0.1
    if len(defines[ident]) > 5:
        mul *= 0.1

    for referencer, num_refs in Counter(references[ident]).items():
        for definer in definers:
            use_mul = mul
            if referencer in chat_rel_fnames:
                use_mul *= 50

            num_refs = math.sqrt(num_refs)
            G.add_edge(referencer, definer, weight=use_mul * num_refs, ident=ident)
```

**PageRank calculation** (lines 500-512):
```python
if personalization:
    pers_args = dict(personalization=personalization, dangling=personalization)
else:
    pers_args = dict()

try:
    ranked = nx.pagerank(G, weight="weight", **pers_args)
except ZeroDivisionError:
    try:
        ranked = nx.pagerank(G, weight="weight")
    except ZeroDivisionError:
        return []
```

**Rank distribution** (lines 514-526):
```python
# Distribute rank from each source node across its out edges
ranked_definitions = defaultdict(float)
for src in G.nodes:
    src_rank = ranked[src]
    total_weight = sum(data["weight"] for _src, _dst, data in G.out_edges(src, data=True))

    for _src, dst, data in G.out_edges(src, data=True):
        data["rank"] = src_rank * data["weight"] / total_weight
        ident = data["ident"]
        ranked_definitions[(dst, ident)] += data["rank"]
```

### Implementation Insights

1. **Why MultiDiGraph?**
   - Allows multiple edges between same nodes (different symbols)
   - Directed edges capture reference direction (referencer → definer)

2. **Why sqrt(num_refs)?**
   - Prevents common utility functions from dominating
   - Balances between "frequently used" and "specifically relevant"

3. **Personalization vs Edge Weights**
   - Personalization: Boosts starting importance of files
   - Edge weights: Determines how importance flows through graph
   - Both work together for context-aware ranking

4. **Token Budget Management**
   - Estimates tokens using sampling (lines 88-100)
   - Iteratively adds definitions until budget exhausted
   - Prioritizes by rank

### Dependencies

- `networkx`: Graph algorithms (PageRank)
- `grep-ast`: Tree-sitter wrapper for symbol extraction
- `diskcache`: Persistent caching
- `pygments`: Fallback lexer for unsupported languages
- `tqdm`: Progress bars for large repos

## 2. Repomix Analysis

### Location
`vendor/repomix/src/` - TypeScript source code

### Directory Structure

```
src/
├── core/
│   ├── packager/          # Main packing logic
│   ├── treeSitter/        # Tree-sitter integration
│   │   ├── queries/       # Language-specific queries
│   │   └── parseStrategies/
│   ├── output/            # Output format generation
│   │   └── outputStyles/  # XML, Markdown, Plain formats
│   ├── file/              # File system operations
│   ├── git/               # Git integration
│   ├── tokenCount/        # Token counting
│   ├── security/          # Security validation
│   ├── metrics/           # Code metrics
│   └── skill/             # Skill generation
├── cli/                   # Command-line interface
├── mcp/                   # MCP server integration
└── config/                # Configuration management
```

### Key Features

1. **Multi-Format Output**
   - XML: Structured format for LLM consumption
   - Markdown: Human-readable format
   - Plain: Simple text format
   - JSON: Machine-readable format

2. **Tree-sitter Integration**
   - Language detection via file extension
   - AST-based code parsing
   - Query-based symbol extraction
   - Multiple parse strategies

3. **Compression Strategies**
   - Remove comments (optional)
   - Remove empty lines
   - Syntax-aware compression
   - Token-budget aware output

4. **Git Integration**
   - Respects `.gitignore`
   - Can include/exclude specific patterns
   - Tracks file metadata

5. **Security Features**
   - Validates file safety
   - Detects sensitive patterns
   - Configurable ignore patterns

### Configuration

Repomix uses `repomix.config.json`:
```json
{
  "output": {
    "filePath": "repomix-output.xml",
    "style": "xml",
    "removeComments": false,
    "removeEmptyLines": false,
    "topFilesLength": 5,
    "showLineNumbers": false,
    "copyToClipboard": false
  },
  "include": [],
  "ignore": {
    "useGitignore": true,
    "useDefaultPatterns": true,
    "customPatterns": []
  },
  "security": {
    "enableSecurityCheck": true
  }
}
```

### Output Format (XML Example)

```xml
<file_summary>
  <purpose>Repository snapshot for AI analysis</purpose>
  <file_format>xml</file_format>
  <number_of_files>42</number_of_files>
  <total_lines>1234</total_lines>
  <total_characters>56789</total_characters>
  <total_tokens>12345</total_tokens>
</file_summary>

<directory_structure>
src/
  core/
    packager/
      index.ts
</directory_structure>

<files>
  <file path="src/core/packager/index.ts">
    <content>
      // File content here
    </content>
  </file>
</files>
```

### Implementation Insights

1. **Why XML?**
   - Structured format easy for LLMs to parse
   - Clear file boundaries
   - Metadata embedded in structure
   - Supports hierarchical organization

2. **Tree-sitter Usage**
   - Parses code into AST
   - Extracts symbols (functions, classes, etc.)
   - Language-agnostic approach
   - Handles syntax errors gracefully

3. **Token Counting**
   - Uses tiktoken (OpenAI's tokenizer)
   - Estimates before generating full output
   - Helps users stay within LLM limits

4. **Performance Optimizations**
   - Worker threads for parallel processing
   - Streaming output generation
   - Incremental file processing
   - Caching parsed results

### Key Files to Study

1. `src/core/packager/` - Main packing logic
2. `src/core/treeSitter/` - Tree-sitter integration
3. `src/core/output/outputGenerate.ts` - Output generation
4. `src/core/output/outputStyles/xmlStyle.ts` - XML format
5. `src/config/configSchema.ts` - Configuration schema

## 3. Tree-sitter Analysis

### Installation Status

- **Python bindings**: v0.25.2 ✅
- **Language pack**: v1.10.2 ✅
- **Note**: Some import issues detected, may need reinstallation

### Key Concepts

1. **Parser**
   - Language-specific parser (e.g., Python, JavaScript)
   - Generates Abstract Syntax Tree (AST)
   - Incremental parsing support
   - Error recovery

2. **Query Language**
   - S-expression based queries
   - Pattern matching on AST nodes
   - Captures named nodes
   - Used for symbol extraction

3. **Language Support**
   - 40+ languages supported
   - Consistent API across languages
   - Community-maintained grammars
   - Easy to add new languages

### Example Usage (Python)

```python
from tree_sitter import Language, Parser
from tree_sitter_languages import get_language, get_parser

# Get language and parser
language = get_language('python')
parser = get_parser('python')

# Parse code
code = b"""
def hello(name):
    print(f"Hello, {name}!")
"""

tree = parser.parse(code)
root_node = tree.root_node

# Query for function definitions
query = language.query("""
(function_definition
  name: (identifier) @function.name)
""")

captures = query.captures(root_node)
for node, capture_name in captures:
    print(f"{capture_name}: {node.text.decode()}")
```

### Query Examples

**Python function definitions**:
```scheme
(function_definition
  name: (identifier) @function.name
  parameters: (parameters) @function.params)
```

**JavaScript class definitions**:
```scheme
(class_declaration
  name: (identifier) @class.name
  body: (class_body) @class.body)
```

**Generic symbol extraction**:
```scheme
[
  (function_definition name: (identifier) @def)
  (class_definition name: (identifier) @def)
  (variable_declaration (identifier) @def)
]
```

### Integration Strategy

For Hippocampus, we should:

1. **Use tree-sitter-languages package**
   - Pre-built binaries for all languages
   - No need to compile grammars
   - Consistent API

2. **Cache parsed trees**
   - Parsing is expensive
   - Cache by file path + mtime
   - Invalidate on file changes

3. **Extract symbols efficiently**
   - Use queries for definitions/references
   - Batch process multiple files
   - Parallel parsing with multiprocessing

4. **Handle errors gracefully**
   - Tree-sitter recovers from syntax errors
   - Partial ASTs still useful
   - Log parsing failures

## 4. ChromaDB Analysis

### Installation Status
⏳ In progress (large dependency tree with many packages)

### Overview
ChromaDB is a vector database designed for AI applications:

- **Embedding storage**: Store code embeddings
- **Similarity search**: Find similar code snippets
- **Persistent storage**: SQLite-based backend
- **Python-native**: Easy integration

### Planned Usage in Hippocampus

1. **LTM Layer - Semantic Search**
   - Embed code snippets using sentence-transformers
   - Store in ChromaDB collections
   - Query by natural language
   - Retrieve relevant code context

2. **Architecture Knowledge**
   - Embed architecture decisions
   - Store design patterns
   - Link to code locations
   - Query for "why" questions

3. **Evolution Tracking**
   - Store snapshots over time
   - Compare embeddings across versions
   - Detect architectural drift
   - Visualize changes

### Example Usage (Planned)

```python
import chromadb
from chromadb.config import Settings

# Initialize client
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=".hippocampus/chroma"
))

# Create collection
collection = client.create_collection(
    name="code_snippets",
    metadata={"description": "Code snippets from repository"}
)

# Add documents
collection.add(
    documents=["def hello(): print('Hello')"],
    metadatas=[{"file": "main.py", "line": 1}],
    ids=["snippet_1"]
)

# Query
results = collection.query(
    query_texts=["function that prints hello"],
    n_results=5
)
```

## 5. NetworkX Analysis

### Status
✅ Already installed (v3.1)

### Key Features for Hippocampus

1. **PageRank Algorithm**
   - Used by Aider for file ranking
   - Supports personalization vector
   - Handles weighted edges
   - Efficient implementation

2. **Graph Algorithms**
   - Shortest paths (dependency chains)
   - Connected components (module boundaries)
   - Centrality measures (key files)
   - Community detection (code clusters)

3. **Graph Visualization**
   - Export to various formats
   - Integration with matplotlib
   - Interactive visualization possible

### Example Usage

```python
import networkx as nx

# Create directed graph
G = nx.DiGraph()

# Add weighted edges
G.add_edge("file_a.py", "file_b.py", weight=10)
G.add_edge("file_b.py", "file_c.py", weight=5)

# Calculate PageRank
ranks = nx.pagerank(G, weight="weight")

# Sort by rank
sorted_files = sorted(ranks.items(), key=lambda x: x[1], reverse=True)
for file, rank in sorted_files:
    print(f"{file}: {rank:.4f}")
```

## Implementation Recommendations

### Phase 2: LTM Layer (Long-Term Memory)

**Priority**: Start here - provides immediate value

**Components**:
1. **Snapshot Generation** (adapt Repomix)
   - Use Repomix as CLI tool initially
   - Generate XML snapshots on commit
   - Store in `.hippocampus/snapshots/`
   - Track metadata (commit hash, timestamp)

2. **Semantic Index** (ChromaDB)
   - Embed snapshot sections
   - Store in ChromaDB collection
   - Enable natural language queries
   - Link to source locations

3. **CLI Commands**
   - `hippo snapshot` - Generate snapshot
   - `hippo search <query>` - Semantic search
   - `hippo history` - View snapshot history
   - `hippo diff <commit1> <commit2>` - Compare snapshots

**Implementation Strategy**:
- Start with Repomix CLI integration (no custom code)
- Add ChromaDB indexing layer
- Build simple CLI wrapper
- Test on claude_codex project

### Phase 3: WM Layer (Working Memory)

**Priority**: After LTM is working

**Components**:
1. **Symbol Extraction** (Tree-sitter)
   - Parse files in current context
   - Extract definitions and references
   - Cache parsed results
   - Handle multiple languages

2. **Repo-Map Generation** (adapt Aider)
   - Build call graph from symbols
   - Calculate PageRank rankings
   - Generate context-aware map
   - Fit within token budget

3. **Dynamic Context**
   - Track files being edited
   - Monitor mentioned identifiers
   - Update personalization vector
   - Regenerate map on changes

**Implementation Strategy**:
- Study Aider's repomap.py in detail
- Extract core algorithm
- Adapt for our use case
- Integrate with tree-sitter-languages

### Phase 4: Integration

**Components**:
1. **Unified Interface**
   - Single CLI entry point
   - Combine LTM and WM queries
   - Intelligent context selection
   - Token budget management

2. **Agent Orchestration**
   - LTM agent: "Where should I look?"
   - WM agent: "What's in this file?"
   - Coordinator: Combines results
   - Feedback loop: Learn from usage

3. **Workflow Integration**
   - Git hooks for snapshots
   - IDE integration (LSP?)
   - CI/CD integration
   - Metrics and monitoring

### Phase 5: Advanced Features

**Components**:
1. **Architecture Evolution**
   - Track changes over time
   - Detect architectural drift
   - Visualize evolution
   - Generate reports

2. **Visualization**
   - Dependency graphs
   - File importance heatmaps
   - Architecture diagrams
   - Interactive exploration

3. **Auto-Documentation**
   - Generate architecture docs
   - Update on changes
   - Link to code
   - Natural language summaries

## Key Takeaways

### What We Learned

1. **Aider's Approach is Brilliant**
   - PageRank naturally captures file importance
   - Personalization makes it context-aware
   - Edge weights encode domain knowledge
   - Scales to large repositories

2. **Repomix is Production-Ready**
   - Well-designed architecture
   - Comprehensive language support
   - Multiple output formats
   - Good performance

3. **Tree-sitter is the Right Choice**
   - Language-agnostic parsing
   - Robust error handling
   - Rich query language
   - Active community

4. **ChromaDB Fits Our Needs**
   - Simple API
   - Persistent storage
   - Good performance
   - Python-native

### What to Adapt vs Build

**Adapt (Use as-is or with minor changes)**:
- Repomix: Use CLI tool directly
- NetworkX: Use library directly
- Tree-sitter-languages: Use library directly
- ChromaDB: Use library directly

**Build (Custom implementation needed)**:
- Repo-map algorithm: Adapt Aider's approach
- Snapshot management: Custom workflow
- Semantic indexing: Custom ChromaDB integration
- CLI interface: Custom commands
- Agent orchestration: Custom logic

### Critical Success Factors

1. **Start Simple**
   - Get LTM working first
   - Use existing tools where possible
   - Iterate based on feedback

2. **Focus on UX**
   - Fast response times
   - Clear output
   - Helpful error messages
   - Good documentation

3. **Test on Real Projects**
   - Use claude_codex as test case
   - Measure actual value
   - Gather feedback
   - Iterate quickly

4. **Performance Matters**
   - Cache aggressively
   - Parallelize where possible
   - Optimize hot paths
   - Monitor resource usage

## Next Steps

### Immediate Actions

1. **Complete ChromaDB Installation**
   - Wait for pip install to finish
   - Test basic functionality
   - Verify embedding generation

2. **Test Repomix on claude_codex**
   ```bash
   cd ~/workspace/claude_codex
   repomix --style xml --output .hippocampus/snapshot.xml
   ```

3. **Study Aider's repomap.py in Detail**
   - Read full implementation
   - Understand all edge cases
   - Document algorithm thoroughly
   - Plan adaptation strategy

4. **Create Phase 2 Implementation Plan**
   - Define exact scope
   - List all tasks
   - Estimate effort
   - Set milestones

### Questions to Answer

1. **LTM Layer**
   - How often to generate snapshots?
   - What embedding model to use?
   - How to chunk code for embedding?
   - What metadata to store?

2. **WM Layer**
   - What token budget for repo-map?
   - How to handle very large repos?
   - When to regenerate map?
   - How to cache effectively?

3. **Integration**
   - How to combine LTM and WM results?
   - What's the user interface?
   - How to measure success?
   - What metrics to track?

## Conclusion

Phase 1 has been highly successful. We now have:

✅ All reference repositories cloned
✅ Key tools installed (Repomix, tree-sitter, networkx)
✅ Deep understanding of Aider's repo-map algorithm
✅ Clear picture of Repomix's architecture
✅ Solid foundation for Phase 2

The path forward is clear:
1. Complete tool installations
2. Test tools on real project
3. Build LTM layer first
4. Add WM layer second
5. Integrate and iterate

We're ready to move to Phase 2: LTM Layer Implementation.
