# Operator: Connect

Purpose: establish explicit semantic, causal, logical, or hierarchical relations between mental models. Keep the models distinct and do not create a broad summary that duplicates them. Prefer updating the relevant focused models with a `## Relations` section. If a separate relation model is genuinely useful, keep it compact and relation-centered. Every written file must contain `## Relations`, with links expressed as `Concept -> relation -> Concept`. Avoid unsupported links.

{input}

{memory}

Return JSON only: {{"summary":"relations established","writes":{{"concept.md":"# complete Markdown file"}}}}
