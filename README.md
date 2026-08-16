# 3M: Mental Model Management: An Operator-Based Framework for LLM Memory

A minimal reference implementation of **Mental Model Management (3M)** for large language models. Instead of storing a growing pile of passages, 3M maintains persistent, concept-centered Markdown models and asks how each model should change when new text arrives.

This repository implements the paper's operator vocabulary:

- Knowledge acquisition: **Extract**, **Retrieve**
- Memory maintenance: **Add**, **Update**, **Merge**, **Split**, **Prune**
- Structural organization: **Connect**, **Compress**, **Abstract**, **Specialize**
- Cognitive processing: **Conflict Detection**, **Conflict Repair**, **Generalize**, **Infer**, **Analogy**, **Find Gap**, **Verify**

The categories overlap. The operators form a vocabulary available to the manager, not a rigid pipeline.

## Design

```text
input text
    -> Extract produces transient candidates
    -> Retrieve selects relevant Markdown files
    -> controller chooses at most five 3M operations
    -> selected operations share transient results and staged files
    -> Verify gates all staged changes
    -> validation + atomic writes + backups
```

All persistent knowledge lives in `memory/*.md`. JSON is used only for transient model/controller responses. There is no vector database, agent framework, or third-party Python runtime dependency.

The manager, rather than the model, enforces the lifecycle. It always runs Extract and Retrieve, limits controller-selected operations, and invokes one final Verify whenever files are staged. A `block` result prevents every proposed change from being committed.

On an empty-memory cold start, Add is mandatory. If an input has at least 400 words and extraction identifies at least three concepts, Add must create between three and seven focused models rather than one comprehensive summary. Every file retains provenance, and extracted questions must survive in at least one `## Knowledge Gaps` section.

## NVIDIA Spark + Ollama

Requires Python 3.10+ and a running Ollama server.

```bash
ollama pull qwen3.6
python3 manager.py examples/es_input.md
```

The requested default tag is `qwen3.6`. Ollama tags vary by installation and release. If that tag is unavailable, install an appropriate Qwen model and configure it without changing code:

```bash
ollama list
THREEM_MODEL=your-qwen-tag python3 manager.py examples/es_input.md
# or
python3 manager.py examples/es_input.md --model your-qwen-tag
```

For an Ollama server on another machine or interface, set `OLLAMA_HOST` or pass `--host`.

## Safe offline demonstration

Preview a deterministic mock cycle without Ollama and without writing memory:

```bash
python3 manager.py examples/es_input.md --mock --dry-run
```

Run it without `--dry-run` to create the sample `success-based-adaptation.md` model. Existing files are written atomically; before replacement, the old version is copied to `memory/.backups/`. The implementation deliberately does not let an LLM delete files. `Prune`, `Merge`, and `Split` can mark or rewrite content, but file deletion remains a human action.

## CLI

```text
python3 manager.py INPUT [--memory DIR] [--prompts DIR]
                          [--model TAG] [--host URL]
                          [--max-operations N] [--max-model-words N]
                          [--mock] [--dry-run]
```

Extract first returns candidate concepts, claims, relations, and gaps without writing memory. Retrieve selects existing files. The controller then sees both transient results and chooses no more than five 3M operations. Later operations receive earlier summaries plus every newly staged file. Finally, Verify either passes the batch, returns corrected versions of staged files, or blocks the commit.

Deterministic contracts keep the model honest:

- semantic filenames must match `# Mental Model: Title`; generic names are rejected;
- one primary concept and at most 1,500 words are allowed per file by default;
- `Infer` requires Premises and Derived Knowledge;
- `Generalize` requires Supporting Observations and Derived Knowledge;
- `Merge` must mark every non-canonical source as superseded;
- `Find Gap` and `Conflict Repair` require their audit sections;
- Verify can correct staged files only and cannot invent a new model.

Ollama generation uses temperature zero for repeatable management decisions. A structurally invalid operator response receives at most two bounded repair attempts; if it still violates a contract, the complete batch is rejected.

## Mental-model convention

The format is intentionally flexible Markdown. The included examples use:

```md
# Mental Model: Concept

## Description
...

## Chunks
- Compact claim.

## Relations
- Concept -> relation -> Other Concept

## Derived Knowledge
- Inference or generalization, clearly labeled.

## Knowledge Gaps
- An unresolved question.

## Provenance
- Source identifier.
```

Keep one primary concept per file and use lowercase slug filenames that match the title, for example `# Mental Model: Mutation Strength` in `mutation-strength.md`. Prompts ask the model to preserve qualifications, provenance, and the distinction between observed and derived knowledge.

## Tests

No Ollama process is needed:

```bash
python3 -m unittest discover -s tests -v
python3 manager.py examples/es_input.md --mock --dry-run
```

## Behavioral benchmark

Six isolated cases evaluate cold-start decomposition, incremental learning, redundancy control, conflict repair, inference, and abstraction:

```bash
python3 benchmark.py --model qwen3.6
```

The runner scores operator behavior, file deltas, required sections and terms, verification, provenance, gap preservation, and pairwise overlap. It also emits a human-review rubric for semantic support and conceptual quality. See `benchmarks/README.md` for the case format and reporting options.

## Recorded NVIDIA Spark run

The repository includes the preserved results of a local Ollama run with `qwen3.6:latest` at temperature zero. A 1,577-word Evolution Strategies input was processed in an initially empty memory using the recorded sequence:

```text
Extract -> Retrieve -> Add -> Connect -> Verify
```

Retrieve returned no prior files. Add created three Markdown mental models, Connect stored their explicit relations, and Verify passed the staged batch before atomic commit. The three committed files contain 471, 260, and 329 words (1,060 words in total), 24 explicit relations, and four knowledge gaps.

The six-case developmental benchmark passed all 67 deterministic checks, with 16 changed-file events, seven new files, and eight distinct selected operator types. Preserved Markdown and the machine-readable report are under `results/qwen3.6-spark/`.

Codex was used to develop the reference software and prompts and to initiate the experiment. The controller decisions, operator responses, and preserved Markdown content were produced by the locally executed Qwen model; Codex did not edit the generated mental-model files afterward. These are single-run developmental results, not a held-out factual evaluation.

## Scope

This is a readable first implementation, not an autonomous truth engine. `Verify` can only use evidence supplied in the input and memory; it must not imply external validation. Model outputs are validated structurally, but users should review significant knowledge changes. For production use, add stronger provenance, schema checks, access control, and evaluation for the chosen model.

## License

MIT. For academic use, citation metadata is provided in `CITATION.cff`.
