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
