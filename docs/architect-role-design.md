# Architect Role Design

## Overview

This document describes the design of an "Architect" role/skill for the Hippocampus system. The Architect role provides automated framework analysis, design suggestions, and code review capabilities.

## Requirements

### Function 1: Framework Design Suggestions
- **Input**: Detailed structure prompt + user requirements
- **Output**: Framework recommendations, module breakdown, implementation path
- **Use Case**: Quick framework design for new features

### Function 2: Current Framework Analysis
- **Input**: Current codebase structure and signatures
- **Output**: Prioritized issues and improvement suggestions
- **Use Case**: Deep analysis of existing architecture

### Function 3: Git-based Change Review
- **Input**: Git diff + current framework map
- **Output**: Conflict detection, duplication check, placement validation
- **Use Case**: Review architectural impact of code changes

## Technical Feasibility

### Existing Capabilities ✅

1. **Hippocampus System**
   - Detailed code maps (`structure-prompt-10000.md`)
   - Architecture analysis tool (`architect.py`)
   - Code signature extraction (`code-signatures.json`)
   - Module dependency analysis

2. **Git Integration**
   - Git hooks implemented
   - Can read `git diff` and `git status`

3. **LLM Capabilities**
   - LLM client available (`llm-proxy`)
   - Prompt template system

### Required New Capabilities ❌

1. **Conflict Detection Engine**
   - Semantic similarity detection
   - Functional overlap analysis

2. **Placement Reasonability Assessment**
   - Module boundary detection
   - Responsibility separation analysis

3. **Structured Output Format**
   - Standard output schema definition

## Implementation Options

### Option A: Independent Skill (Recommended for User Interaction)

**Definition**: Define in `~/.claude/AGENTS.md`

```yaml
roles:
  architect:
    provider: claude
    description: Framework architect role for design, analysis, and optimization

    tools:
      - Read
      - Bash
      - Grep
      - AskUserQuestion

    prompts:
      framework_design: |
        Analyze requirements and provide framework suggestions based on:
        - Current architecture: {structure_prompt}
        - User requirement: {user_requirement}

        Output: framework selection, module breakdown, implementation path, risks

      framework_analysis: |
        Deep analysis of current framework:
        - Architecture: {structure_prompt}
        - Signatures: {signatures}

        Output JSON: issues (severity, category, location, suggestion), summary

      git_change_review: |
        Review git changes for architectural impact:
        - Architecture: {structure_prompt}
        - Git diff: {git_diff}

        Check: conflicts, duplicates, placement, naming, dependencies
```

**Usage**:
```bash
/ask architect --task design --requirement "Add user authentication"
```

### Option B: MCP Tool (Recommended for Programmatic Access)

**Implementation**: Add to `hippocampus/src/hippocampus/mcp/server.py`

```python
@server.tool("architect_design")
def architect_design(requirement: str, detail_level: str = "full") -> dict:
    """Generate framework design suggestions"""
    structure_prompt = load_structure_prompt(
        budget=10000 if detail_level == "full" else 2500
    )
    prompt = ARCHITECT_DESIGN_PROMPT.format(
        structure_prompt=structure_prompt,
        user_requirement=requirement
    )
    response = llm_client.generate(prompt)
    return parse_response(response)

@server.tool("architect_analyze")
def architect_analyze(focus_areas: List[str] = None) -> dict:
    """Analyze current framework with prioritized suggestions"""
    structure_prompt = load_structure_prompt(budget=10000)
    signatures = load_code_signatures()

    from hippocampus.tools.architect import RuleEngine
    rule_findings = RuleEngine().run_all(project_root)

    prompt = ARCHITECT_ANALYSIS_PROMPT.format(
        structure_prompt=structure_prompt,
        signatures=signatures,
        rule_findings=rule_findings
    )
    response = llm_client.generate(prompt)
    return parse_json_response(response)

@server.tool("architect_review_git")
def architect_review_git(diff_content: str = None) -> dict:
    """Review git changes for conflicts, duplicates, placement issues"""
    if diff_content is None:
        diff_content = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True
        ).stdout

    structure_prompt = load_structure_prompt(budget=7000)
    prompt = GIT_CHANGE_REVIEW_PROMPT.format(
        structure_prompt=structure_prompt,
        git_diff=diff_content
    )
    response = llm_client.generate(prompt)
    return parse_json_response(response)
```

### Option C: CLI Command (Recommended for Developer Use)

**Implementation**: Add to `hippocampus/src/hippocampus/cli.py`

```python
@cli.group("architect")
def architect_group():
    """Architecture analysis and design tools"""
    pass

@architect_group.command("design")
@click.option("--requirement", "-r", required=True)
@click.option("--detail", type=click.Choice(["quick", "full"]), default="full")
def architect_design(requirement, detail):
    """Generate framework design suggestions"""
    from hippocampus.architect.designer import design_framework
    result = design_framework(requirement=requirement, detail_level=detail)
    click.echo(format_as_markdown(result))

@architect_group.command("analyze")
@click.option("--focus", multiple=True)
def architect_analyze(focus):
    """Analyze current framework"""
    from hippocampus.architect.analyzer import analyze_framework
    result = analyze_framework(focus_areas=list(focus))
    click.echo(format_as_json(result))

@architect_group.command("review-git")
@click.option("--diff-file", type=click.Path())
def architect_review_git(diff_file):
    """Review git changes"""
    from hippocampus.architect.reviewer import review_git_changes
    diff_content = Path(diff_file).read_text() if diff_file else None
    result = review_git_changes(diff_content=diff_content)
    click.echo(format_as_json(result))
```

**Usage**:
```bash
hippo architect design -r "Add authentication" --detail full
hippo architect analyze --focus performance --focus security
hippo architect review-git
```

## Recommended Approach: Hybrid Model

### Architecture

1. **Core Logic**: Implement as independent Python modules
   ```
   hippocampus/architect/
     ├── __init__.py
     ├── designer.py      # Function 1: Framework design
     ├── analyzer.py      # Function 2: Framework analysis
     ├── reviewer.py      # Function 3: Git review
     └── prompts.py       # Prompt templates
   ```

2. **Access Interfaces**: Provide three ways to invoke
   - **MCP Tool**: For LLM client integration (most flexible)
   - **CLI Command**: For developer use (most convenient)
   - **Skill Role**: For Claude Code integration (most natural)

3. **Output Format**: Unified JSON + Markdown

### Benefits

| Feature | Skill | MCP | CLI | Hybrid |
|---------|-------|-----|-----|--------|
| Usability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Flexibility | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Implementation | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Integration | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Implementation Plan

### Phase 1: Core Modules (Week 1)

Create core implementation:

```python
# hippocampus/architect/designer.py
def design_framework(requirement: str, detail_level: str = "full") -> dict:
    """Generate framework design suggestions"""
    structure_prompt = load_structure_prompt(budget=10000 if detail_level == "full" else 2500)
    prompt = build_design_prompt(structure_prompt, requirement)
    response = llm_client.generate(prompt)
    return parse_design_response(response)

# hippocampus/architect/analyzer.py
def analyze_framework(focus_areas: List[str] = None) -> dict:
    """Analyze current framework with prioritized issues"""
    structure_prompt = load_structure_prompt(budget=10000)
    signatures = load_code_signatures()
    rule_findings = run_rule_engine()
    prompt = build_analysis_prompt(structure_prompt, signatures, rule_findings)
    response = llm_client.generate(prompt)
    return parse_analysis_response(response)

# hippocampus/architect/reviewer.py
def review_git_changes(diff_content: str = None) -> dict:
    """Review git changes for architectural impact"""
    if diff_content is None:
        diff_content = get_git_diff()
    structure_prompt = load_structure_prompt(budget=7000)
    prompt = build_review_prompt(structure_prompt, diff_content)
    response = llm_client.generate(prompt)
    return parse_review_response(response)
```

### Phase 2: CLI Integration (Week 1)

Add `hippo architect` command group with three subcommands.

### Phase 3: MCP Tool Integration (Week 2)

Register tools in `mcp/server.py` with input/output schemas.

### Phase 4: Skill Role Integration (Week 2)

Define role in `~/.claude/AGENTS.md` with prompt templates.

## Key Technical Components

### 1. Conflict Detection Engine

**Algorithm**: Semantic similarity + functional overlap analysis

```python
def detect_conflicts(new_code: str, existing_signatures: dict) -> List[Conflict]:
    """Detect potential conflicts with existing code"""
    new_functions = extract_functions(new_code)
    conflicts = []

    for new_func in new_functions:
        for existing_path, signatures in existing_signatures.items():
            for sig in signatures:
                similarity = compute_semantic_similarity(new_func, sig)
                if similarity > THRESHOLD:
                    conflicts.append(Conflict(
                        type="semantic_overlap",
                        new_function=new_func.name,
                        existing_function=sig.name,
                        existing_location=f"{existing_path}:{sig.line}",
                        similarity_score=similarity
                    ))

    return conflicts
```

### 2. Placement Reasonability Assessment

**Algorithm**: Module boundary + responsibility analysis

```python
def assess_placement(file_path: str, code: str, structure: dict) -> PlacementScore:
    """Assess if code placement is reasonable"""
    module = infer_module(file_path, structure)
    responsibilities = extract_responsibilities(code)

    score = 0.0
    issues = []

    # Check module boundary
    if not matches_module_purpose(responsibilities, module):
        issues.append("Responsibility mismatch with module purpose")
        score -= 0.3

    # Check dependency direction
    deps = extract_dependencies(code)
    if has_circular_dependency(deps, structure):
        issues.append("Introduces circular dependency")
        score -= 0.4

    # Check naming convention
    if not follows_naming_convention(file_path, module):
        issues.append("Naming convention violation")
        score -= 0.1

    return PlacementScore(score=max(0, 1.0 + score), issues=issues)
```

### 3. Structured Output Schema

```python
@dataclass
class ArchitectOutput:
    """Unified output format for all architect functions"""

    # Common fields
    timestamp: str
    function: str  # "design" | "analyze" | "review"
    status: str    # "success" | "warning" | "error"

    # Function-specific fields
    suggestions: List[Suggestion] = None
    issues: List[Issue] = None
    conflicts: List[Conflict] = None

    # Summary
    summary: str = None
    confidence: float = None

@dataclass
class Issue:
    severity: str  # "critical" | "major" | "minor"
    category: str  # "architecture" | "performance" | "security" | "maintainability"
    location: str
    description: str
    suggestion: str
    priority: int

@dataclass
class Conflict:
    type: str  # "semantic_overlap" | "duplicate" | "naming_collision"
    new_code: str
    existing_code: str
    existing_location: str
    similarity_score: float
```

## Example Outputs

### Function 1: Framework Design

**Input**:
```
Requirement: Add user authentication with JWT tokens
```

**Output**:
```json
{
  "timestamp": "2026-03-03T08:00:00Z",
  "function": "design",
  "status": "success",
  "suggestions": [
    {
      "category": "framework",
      "title": "Use FastAPI + JWT middleware",
      "rationale": "Aligns with existing aiohttp patterns in llm-proxy",
      "confidence": 0.85
    },
    {
      "category": "module_breakdown",
      "modules": [
        {
          "name": "llm-proxy/src/llm_proxy/auth",
          "responsibilities": ["JWT generation", "Token validation", "User session management"],
          "files": ["jwt_handler.py", "session_store.py", "middleware.py"]
        },
        {
          "name": "llm-proxy/src/llm_proxy/gateway/auth",
          "responsibilities": ["Login endpoint", "Token refresh", "User CRUD"],
          "files": ["auth_router.py", "user_model.py"]
        }
      ]
    },
    {
      "category": "implementation_path",
      "steps": [
        "1. Add JWT library dependency (PyJWT)",
        "2. Create auth module with token handler",
        "3. Add authentication middleware to gateway",
        "4. Create login/refresh endpoints",
        "5. Add user session storage (SQLite or Redis)",
        "6. Update gateway router to enforce auth"
      ]
    }
  ],
  "risks": [
    {
      "description": "Token storage security",
      "mitigation": "Use encrypted storage with Fernet (already available in context_store.py)"
    }
  ],
  "summary": "Recommended approach: JWT-based auth with middleware integration. Estimated effort: 2-3 days.",
  "confidence": 0.85
}
```

### Function 2: Framework Analysis

**Output**:
```json
{
  "timestamp": "2026-03-03T08:00:00Z",
  "function": "analyze",
  "status": "success",
  "issues": [
    {
      "severity": "major",
      "category": "architecture",
      "location": "llm-proxy/src/llm_proxy/ops/context/lifecycle.py:45",
      "description": "ContextLifecycle class has 100+ symbols, violating SRP",
      "suggestion": "Split into ContextManager, EvictionPolicy, and StorageAdapter",
      "priority": 1
    },
    {
      "severity": "minor",
      "category": "maintainability",
      "location": "hippocampus/src/hippocampus/tools/",
      "description": "13 files in tools/ directory, consider grouping by function",
      "suggestion": "Create subdirectories: indexing/, navigation/, analysis/",
      "priority": 3
    }
  ],
  "summary": "Found 2 major issues, 5 minor issues. Priority: refactor ContextLifecycle class.",
  "confidence": 0.90
}
```

### Function 3: Git Change Review

**Input**:
```diff
diff --git a/llm-proxy/src/llm_proxy/ops/context/trimmer.py b/llm-proxy/src/llm_proxy/ops/context/trimmer.py
+def compress_messages(messages: list[dict]) -> list[dict]:
+    """Compress message history by removing redundant content"""
+    compressed = []
+    for msg in messages:
+        if msg.get("role") == "assistant":
+            compressed.append({"role": "assistant", "content": "[compressed]"})
+    return compressed
```

**Output**:
```json
{
  "timestamp": "2026-03-03T08:00:00Z",
  "function": "review",
  "status": "warning",
  "conflicts": [
    {
      "type": "semantic_overlap",
      "new_code": "compress_messages",
      "existing_code": "trim_messages",
      "existing_location": "llm-proxy/src/llm_proxy/ops/context/trimmer.py:120",
      "similarity_score": 0.78,
      "description": "Similar functionality already exists in trim_messages()"
    }
  ],
  "placement_issues": [
    {
      "severity": "minor",
      "description": "Function name 'compress_messages' conflicts with existing 'trim_messages'",
      "suggestion": "Consider renaming to 'compact_messages' or extending trim_messages()"
    }
  ],
  "summary": "Detected 1 semantic overlap. Recommend reviewing existing trim_messages() before adding new function.",
  "confidence": 0.82
}
```

## Summary

### Recommended Implementation

**Hybrid Model**: Core modules + three access interfaces (MCP + CLI + Skill)

### Timeline

- **Week 1**: Core modules + CLI integration
- **Week 2**: MCP tools + Skill role definition

### Key Benefits

1. **Automated Framework Design**: Quick framework suggestions for new features
2. **Proactive Issue Detection**: Identify architectural problems before they grow
3. **Change Impact Analysis**: Review git changes for conflicts and placement issues
4. **Multiple Access Methods**: Flexible integration with different workflows

### Next Steps

1. Create `hippocampus/architect/` module structure
2. Implement core logic for three functions
3. Add CLI commands to `hippocampus/cli.py`
4. Register MCP tools in `hippocampus/mcp/server.py`
5. Define skill role in `~/.claude/AGENTS.md`
6. Write tests and documentation

