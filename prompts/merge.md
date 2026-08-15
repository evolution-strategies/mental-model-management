# Operator: Merge

Purpose: combine mental models only when they substantially represent the same concept. Keep one semantic canonical filename. Rewrite every non-canonical source and never delete it. A superseded file MUST begin with `# Mental Model: Original Title (Superseded)` as its first nonblank line; place `Status: Superseded by [Title](canonical-file.md)` immediately after that heading. Never put status text before the heading. Do not merge merely related concepts.

{input}

{memory}

Return JSON only: {{"summary":"merge decision","metadata":{{"canonical_file":"semantic-concept.md","merged_sources":["semantic-concept.md","alias.md"],"supersedes":["alias.md"]}},"writes":{{"semantic-concept.md":"# complete canonical Markdown","alias.md":"# complete Markdown marked Superseded by"}}}}
