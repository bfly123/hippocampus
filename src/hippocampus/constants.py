"""Default paths, schema versions, and supported languages."""

# Directory names
HIPPO_DIR = ".hippocampus"
QUERIES_DIR = "queries"

# Snapshot directory
SNAPSHOTS_DIR = "snapshots"

# Output filenames
CODE_SIGNATURES_FILE = "code-signatures.json"
TREE_FILE = "tree.json"
TREE_DIFF_FILE = "tree-diff.json"
STRUCTURE_PROMPT_FILE = "structure-prompt.md"
TRIMMED_FILE = "repomix-compress-trimmed.json"
INDEX_FILE = "hippocampus-index.json"
PHASE1_CACHE_FILE = "phase1-cache.json"
PHASE2_CACHE_FILE = "phase2-cache.json"
PHASE3_CACHE_FILE = "phase3-cache.json"
CONFIG_FILE = "config.yaml"
TAG_VOCAB_FILE = "tag-vocab.json"
MEMORY_RECORDS_FILE = "memory-records.jsonl"
MEMORY_METADATA_FILE = "memory-metadata.json"
ARCHITECT_REPORT_FILE = "architect-report.json"
ARCHITECT_METRICS_FILE = "architect-metrics.json"

# Schema versions
SIGNATURES_SCHEMA_VERSION = 1
INDEX_SCHEMA_VERSION = 2
TREE_SCHEMA_VERSION = 1

# Token estimation ratio (chars per token, rough average)
CHARS_PER_TOKEN = 4

# Default trimmer budget
DEFAULT_TRIM_BUDGET = 10000

# LLM defaults
DEFAULT_MAX_CONCURRENT = 20
DEFAULT_RETRY_MAX = 3
DEFAULT_TIMEOUT = 30
