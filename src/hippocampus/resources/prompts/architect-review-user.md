## Architecture Data
{summary}

## Rule Engine Findings (current state)
{findings_text}

## Recent Commits
```
{git_log}
```

## Change Stats
```
{git_diff}
```

## Diff Content
```diff
{content_diff}
```

## Task
Evaluate the architectural impact of these commits. For each commit, assess:
- Does it respect module boundaries?
- Does it introduce new dependencies? Are they in the right direction?
- Does it increase or decrease architectural debt?

## Output
Return valid JSON only:
{{
    "summary": "<overall assessment>",
    "commit_assessments": [
        {{
            "commit": "<hash + message>",
            "impact": "positive"|"neutral"|"negative",
            "notes": "<brief explanation>"
        }}
    ],
    "new_risks": ["<risk if any>"],
    "overall_trend": "improving"|"stable"|"degrading"
}}
