# Operator: Extract

Purpose: transform input text into transient candidate concepts and compact claims. Preserve qualifications and distinguish direct observations from derived claims. Extraction proposes knowledge; it does not append a document summary and never writes memory.

Inspect INPUT and MEMORY. Return complete replacement/new Markdown files only when extraction itself should persist an intake model; normally return no writes because later integration operators persist candidates.

{input}

{memory}

Return JSON only:
{{"summary":"brief extraction summary","candidates":{{"concepts":["Concept"],"claims":[{{"text":"qualified claim","kind":"observed"}}],"relations":["A -> relation -> B"],"gaps":["unanswered question"]}},"writes":{{}}}}
