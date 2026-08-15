# Operator: Conflict Detection

Purpose: identify chunks that appear incompatible. Do not silently choose a winner or delete either claim. Record the claims, contexts, provenance, and why they conflict so Conflict Repair can examine them.

{input}

{memory}

Return JSON only: {{"summary":"conflicts found","writes":{{"conflicts.md":"# complete Markdown file"}}}}

