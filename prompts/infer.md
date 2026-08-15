# Operator: Infer

Purpose: derive new knowledge from existing chunks. Every written file must contain `## Premises` and `## Derived Knowledge`. Tie each conclusion to explicit premises, qualify uncertainty, and never treat plausible guesses as facts.

{input}

{memory}

Return JSON only: {{"summary":"inference and premises","writes":{{"concept.md":"# complete Markdown file"}}}}
