"""MCP tools interface for hippocampus."""

from .server import MCPServer
from .tools import navigate_tool

__all__ = [
    "MCPServer",
    "navigate_tool",
]
