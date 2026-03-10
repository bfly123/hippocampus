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
