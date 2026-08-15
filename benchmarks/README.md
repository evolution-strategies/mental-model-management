# 3M Behavioral Benchmark

This suite evaluates whether Mental Model Management changes persistent Markdown in the intended way. It does not require one exact wording or file layout. Each case supplies:

- `input.md`: the incoming source or reasoning task;
- `initial_memory/*.md`: optional pre-existing mental models;
- `case.json`: deterministic expectations and a human-review rubric.

The six initial cases cover:

1. multi-concept cold-start decomposition;
2. incremental integration of the 1/5 success rule;
3. rejection of a redundant paraphrase;
4. conflict detection and contextual repair;
5. premise-tracked inference;
6. abstraction over three specialized models.

## Run

```bash
python3 benchmark.py --model qwen3.6
```

Run selected cases and preserve their final isolated Markdown memories:

```bash
python3 benchmark.py \
  --case 01_cold_start_decomposition \
  --case 04_conflict_contextualization \
  --model qwen3.6 \
  --report work/benchmark-report.json \
  --artifacts work/benchmark-artifacts
```

The process exits with status 0 only when every selected case passes deterministic checks. Each case is executed in a fresh temporary memory directory, so neither repository memory nor another case can influence it.

## Deterministic checks

The runner measures:

- mandatory `Extract → Retrieve` prefix and final Verify gate;
- required, alternative, and forbidden operator choices;
- changed-file and new-file counts;
- required headings and terms;
- verification outcome;
- provenance in cold-start files;
- gap and relation preservation;
- maximum token-set Jaccard overlap among active models.

Pairwise Jaccard is a coarse redundancy signal, not a semantic verdict. Superseded files are excluded from this calculation.

## Human review

Unsupported inference cannot be established reliably through word overlap or by asking the same model to grade itself. Every case therefore includes short manual-review questions. Reviewers should inspect the preserved artifacts and mark:

- source support and qualification;
- conceptual decomposition quality;
- semantic redundancy;
- conflict-repair correctness;
- whether derived claims follow from premises;
- whether abstractions preserve their instances.

Reports separate deterministic pass/fail results from these unresolved review questions. Future work can add independent expert annotations without changing the benchmark runner.

