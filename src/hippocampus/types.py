"""Pydantic data models for all JSON schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── code-signatures.json models ──

class Signature(BaseModel):
    name: str
    kind: str  # class, function, method, const, etc.
    line: int
    parent: Optional[str] = None


class FileSignatures(BaseModel):
    lang: str
    signatures: list[Signature] = Field(default_factory=list)


class CodeSignaturesDoc(BaseModel):
    version: int = 1
    generated_at: str = ""
    files: dict[str, FileSignatures] = Field(default_factory=dict)


# ── tree.json models ──

class TreeNode(BaseModel):
    id: str
    type: str  # "dir" or "file"
    name: str
    children: list[TreeNode] = Field(default_factory=list)


class TreeDoc(BaseModel):
    version: int = 1
    generated_at: str = ""
    root: TreeNode = Field(default_factory=lambda: TreeNode(
        id="dir:.", type="dir", name="."
    ))


# ── tree-diff.json models ──

class DiffEntry(BaseModel):
    id: str
    type: str
    name: str
    change: str  # "added", "removed", "modified"


class TreeDiffDoc(BaseModel):
    version: int = 1
    generated_at: str = ""
    baseline_at: str = ""
    changes: list[DiffEntry] = Field(default_factory=list)
