"""MCP server for hippocampus navigation tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .tools import navigate_tool


class MCPServer:
    """Simple MCP server for hippocampus tools."""
    
    def __init__(self, hippo_dir: Path = None):
        self.hippo_dir = hippo_dir or Path.cwd() / ".hippocampus"
        self.tools = {
            "hippo.navigate": self._handle_navigate,
        }
    
    def _handle_navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle navigate tool call."""
        return navigate_tool(
            query=params.get("query", ""),
            focus_files=params.get("focus_files"),
            snapshot_ref=params.get("snapshot_ref"),
            budget_tokens=params.get("budget_tokens", 5000),
            hippo_dir=self.hippo_dir,
        )
    
    def handle_tool_call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call."""
        handler = self.tools.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            return handler(params)
        except Exception as e:
            return {"error": str(e)}
