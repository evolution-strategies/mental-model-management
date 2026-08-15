# Contributing

Contributions that keep the reference implementation small, inspectable, and faithful to the 3M operator vocabulary are welcome.

## Development

The runtime uses Python 3.10+ and the standard library. No Ollama process is required for the offline checks:

```bash
python3 -m unittest discover -s tests -v
python3 manager.py examples/es_input.md --mock --dry-run
```

Please include tests for behavior changes. A new or revised operator must retain its dedicated prompt in `prompts/`. Persistent memory must remain Markdown; JSON may be used only for transient model responses.

## Benchmark cases

New cases belong under `benchmarks/cases/` and should specify deterministic structural expectations plus short human-review questions. Avoid exact-text matching when several concept organizations could be valid. Keep model-generated benchmark results separate from the deterministic offline test suite.

## Safety and scope

Do not add direct LLM-controlled deletion. Existing Markdown must continue to use validation, atomic replacement, and backups. Large frameworks, databases, or new runtime dependencies should be justified by a concrete capability that cannot remain small and local.

