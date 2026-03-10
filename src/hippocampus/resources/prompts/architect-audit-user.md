## Architecture Data
{summary}

## Rule Engine Findings
{findings_text}

## Analysis Framework
Apply these principles:
1. **Stable Dependencies Principle (SDP)**: Dependencies should flow toward stability.
   Evaluate whether dependency directions are reasonable.
2. **C4 Model**: Assess health at Component (module) and Code (class/function) levels.

## Output
Return valid JSON only:
{{
    "health_score": <0-100>,
    "summary": "<2-3 sentence overall assessment>",
    "root_causes": ["<root cause 1>", ...],
    "recommendations": [
        {{"priority": "high"|"medium"|"low", "action": "<specific action>"}}
    ],
    "sdp_assessment": "<1-2 sentences on dependency direction health>"
}}
