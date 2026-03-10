## Architecture Data
{summary}

## Feature Description
{description}

## Task
Determine the best placement for this feature within the existing architecture.
Consider module boundaries, dependency directions, and the Stable Dependencies Principle.

## Output
Return valid JSON only:
{{
    "target_module": "<existing module ID or 'new:suggested-name'>",
    "rationale": "<why this module>",
    "files_to_create": [
        {{"path": "<file path>", "purpose": "<what it does>"}}
    ],
    "files_to_modify": [
        {{"path": "<file path>", "changes": "<what to change>"}}
    ],
    "new_dependencies": [
        {{"from": "<module>", "to": "<module>", "reason": "<why>"}}
    ],
    "risks": ["<risk 1>", ...],
    "impact_blast_radius": ["<existing file that will be affected>", ...],
    "integration_seams": [
        {{"file": "<file path>", "function": "<function name>", "action": "<how to integrate>"}}
    ]
}}
