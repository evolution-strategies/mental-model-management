# Operator: Add

Purpose: introduce genuinely new knowledge that is not already represented. Add compact chunks to existing concept models or create semantic lowercase-slug.md models. On a multi-concept cold start, create several focused files in one response rather than one comprehensive source summary. Keep cross-concept statements as relations. Preserve extracted unresolved questions under `## Knowledge Gaps` in the most relevant model. Do not duplicate paraphrases. Every written file must include `## Provenance` with the supplied source label.

{input}

{memory}

Return JSON only: {{"summary":"what was added","writes":{{"semantic-concept.md":"# complete Markdown file","another-concept.md":"# complete Markdown file"}}}}
