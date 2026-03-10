"""Prompt templates for each pipeline phase."""

from __future__ import annotations


PHASE_1_SYSTEM = (
    "You are a code analysis assistant. Based on the provided file content "
    "and signature information, generate a description, tags, and signature "
    "descriptions for each file. Output JSON only, no explanations."
)

PHASE_1_USER = """\
Analyze the following file and output JSON:

File path: {file_path}
Language: {lang}

Directory structure (context):
{dir_tree}

File content (compressed):
{compress_content}

Extracted signatures:
{signatures}

Tag vocabulary (grouped by dimension):
{tag_vocab}

Output format:
{{
  "desc": "File function description (<=50 chars)",
  "tags": ["tag1", "tag2", "tag3"],
  "signatures": [
    {{"name": "signature name", "desc": "Signature function description (<=30 chars)"}}
  ]
}}

desc must be in {lang_hint}, concise and accurate.
tags: select 3-5 from the vocabulary above. If insufficient, you may propose at most 1 new tag (lowercase, hyphens allowed, <=15 chars).
signatures array length must equal the extracted signature count {sig_count}.
"""

PHASE_2A_SYSTEM = (
    "You are a software architecture analyst. Generate a module vocabulary "
    "from the file list. Output JSON only, no explanations."
)

PHASE_2A_USER = """\
Here are all project files with their descriptions and tags:

{file_summaries}

Cluster these files into 8-15 logical modules. Output JSON:
{{
  "modules": [
    {{"id": "mod:module-name", "desc": "Module description (<=80 chars)"}}
  ]
}}

Module id format: mod:lowercase-hyphenated. Count: 8-15 modules.
"""

PHASE_2B_SYSTEM = (
    "You are a code classification assistant. Assign files to the defined "
    "modules. Output JSON only, no explanations."
)

PHASE_2B_USER = """\
Module vocabulary:
{module_vocab}

File list (path + description + tags):
{file_summaries}

Assign a module_id to each file. Output JSON array:
[
  {{"file": "path", "module_id": "mod:xxx"}}
]

Array length must equal the file count {file_count}.
module_id must come from the vocabulary above.
"""

PHASE_3A_SYSTEM = (
    "You are a software architecture analyst. Generate a description and "
    "key file list for the module. Output JSON only, no explanations."
)

PHASE_3A_USER = """\
Module: {module_id}
Module summary: {module_desc}

Files in this module:
{module_files}

Output JSON:
{{
  "desc": "Detailed module description (<=100 chars)",
  "key_files": ["key_file_path1", "key_file_path2"]
}}

key_files must be a subset of the file list above, select 3-5 most important ones.
"""

PHASE_3B_SYSTEM = (
    "You are a software architecture analyst. Generate a project-level "
    "overview description. Output JSON only, no explanations."
)

PHASE_3B_USER = """\
Project module overview:
{module_summaries}

README excerpt:
{readme_excerpt}

Output JSON:
{{
  "overview": "Overall project description (<=200 chars)",
  "architecture": "Architecture style description (<=50 chars)",
  "scale": {{
    "files": {file_count},
    "modules": {module_count},
    "primary_lang": "{primary_lang}"
  }}
}}
"""
