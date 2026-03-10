"""Tree-sitter API compatibility layer for Aider vendor code.

This module provides a compatibility shim for tree-sitter 0.25.x API changes.
The main issue is that Query.captures() was removed in favor of QueryCursor.

Since tree_sitter.Query is an immutable C extension type, we can't monkey-patch it.
Instead, we patch the grep_ast.tsl module to wrap Query objects.

Reference: https://github.com/tree-sitter/py-tree-sitter/blob/master/CHANGELOG.md

tree-sitter 0.25.x API:
    query = Query(language, source)
    cursor = QueryCursor(query)
    matches = cursor.matches(node)  # Returns: list[(pattern_index, captures_dict)]
    # captures_dict format: {capture_name: [nodes]}
"""

from __future__ import annotations

import sys
import tree_sitter


class QueryWrapper:
    """Wrapper for tree_sitter.Query that adds back captures() method."""

    def __init__(self, query):
        self._query = query

    def captures(self, node, start_point=None, end_point=None):
        """Compatibility wrapper for Query.captures() using new QueryCursor API.

        Old API (tree-sitter < 0.25):
            captures = query.captures(node)
            # Returns: dict[str, list[Node]]

        New API (tree-sitter >= 0.25):
            cursor = QueryCursor(query)
            matches = cursor.matches(node)
            # Returns: list[(pattern_index, captures_dict)]
            # captures_dict format: {capture_name: [nodes]}
        """
        # Create QueryCursor with the query
        cursor = tree_sitter.QueryCursor(self._query)

        # Execute query and get matches
        matches = cursor.matches(node)

        # Aggregate all captures from all matches
        # Return format: dict[str, list[Node]] (for USING_TSL_PACK=True)
        captures_dict = {}
        for pattern_index, match_captures in matches:
            for capture_name, nodes in match_captures.items():
                if capture_name not in captures_dict:
                    captures_dict[capture_name] = []
                captures_dict[capture_name].extend(nodes)

        return captures_dict

    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped query."""
        return getattr(self._query, name)


def patch_grep_ast_tsl():
    """Patch grep_ast.tsl to wrap Language.query() method.

    This intercepts the query creation and wraps it with our compatibility layer.
    """
    try:
        # Import grep_ast.tsl
        if 'grep_ast.tsl' in sys.modules:
            # Already imported, need to patch the existing module
            tsl_module = sys.modules['grep_ast.tsl']
        else:
            import grep_ast.tsl as tsl_module

        # Check if we're using TSL_PACK (tree-sitter-language-pack)
        if not hasattr(tsl_module, 'USING_TSL_PACK') or not tsl_module.USING_TSL_PACK:
            # Not using TSL_PACK, no need to patch
            return True

        # Get the Language class
        from tree_sitter_language_pack import Language

        # Store original query method
        if not hasattr(Language, '_original_query'):
            Language._original_query = Language.query

            # Wrap the query method
            def query_wrapper(self, source):
                """Wrapped query method that returns QueryWrapper."""
                # Use new Query constructor instead of deprecated query() method
                original_query = tree_sitter.Query(self, source)
                return QueryWrapper(original_query)

            Language.query = query_wrapper

        return True

    except Exception as e:
        # If patching fails, return False
        import traceback
        print(f"Failed to patch grep_ast.tsl: {e}")
        traceback.print_exc()
        return False


def ensure_compatibility():
    """Ensure tree-sitter API compatibility for Aider vendor code.

    Call this before importing Aider's repomap module.
    """
    try:
        return patch_grep_ast_tsl()
    except Exception as e:
        # If patching fails, return False to indicate incompatibility
        import traceback
        print(f"Compatibility patch failed: {e}")
        traceback.print_exc()
        return False

