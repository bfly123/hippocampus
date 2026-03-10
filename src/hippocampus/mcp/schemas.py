"""MCP tool schemas for hippocampus."""

from typing import List, Optional, TypedDict


class NavigateInput(TypedDict):
    """Input schema for hippo.navigate tool."""
    query: str
    focus_files: Optional[List[str]]
    snapshot_ref: Optional[str]
    budget_tokens: Optional[int]


class SnippetInfo(TypedDict):
    """Single code snippet."""
    lois: List[int]        # Lines of interest used for rendering
    symbols: List[str]     # Symbol names in this snippet
    content: str           # Rendered code content (may have ellipses)
    tokens: int            # Token count


class FileSnippets(TypedDict):
    """Snippets from a single file."""
    file: str              # Relative file path
    rank: float            # File importance score
    snippets: List[SnippetInfo]
    total_tokens: int      # Sum of all snippet tokens


class RankedFile(TypedDict):
    """Single ranked file entry."""
    file: str
    rank: float
    tier: int


class NavigateOutput(TypedDict):
    """Output schema for hippo.navigate tool."""
    ranked_files: List[RankedFile]
    explanation: str
    context_snippets: List[FileSnippets]


class SymbolRefsInput(TypedDict):
    """Input schema for hippo.symbol_refs tool."""
    symbol: str
    snapshot_ref: Optional[str]
    depth: Optional[int]
