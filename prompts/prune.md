# Operator: Prune

Purpose: remove chunks that are obsolete, rejected, redundant, or fully subsumed by a better canonical chunk. Pruning removes information; it does not synthesize a replacement. Be conservative. This implementation may remove chunks inside a file but never deletes a file automatically.

{input}

{memory}

Return JSON only: {{"summary":"what was pruned and why","writes":{{"concept.md":"# complete Markdown file"}}}}

