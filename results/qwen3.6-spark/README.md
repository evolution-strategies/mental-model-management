# Qwen 3.6 on NVIDIA Spark

These files preserve the results described in the reference implementation's demonstration and developmental benchmark.

## Environment

- Hardware: NVIDIA Spark
- Inference server: local Ollama
- Model: `qwen3.6:latest`
- Temperature: `0`
- Persistent representation: Markdown
- Benchmark run recorded: 2026-08-15

## Cold-start demonstration

The 1,577-word input in `examples/es_input.md` was processed with an empty mental-model directory. The manager executed:

```text
Extract -> Retrieve -> Add -> Connect -> Verify
```

Retrieve returned no existing models. The remaining operations created, connected, verified, and committed the three files in `cold-start/`.

| File | Words |
| --- | ---: |
| `evolution-strategies.md` | 471 |
| `covariance-matrix-adaptation.md` | 260 |
| `search-distribution-adaptation.md` | 329 |
| **Total** | **1,060** |

The files contain 24 explicit relations and four knowledge gaps. Their combined word count is 67.2% of the input word count.

## Behavioral benchmark

`benchmark-report.json` contains the full machine-readable report for six isolated cases. All six cases passed all 67 deterministic checks. Across the cases, the controller selected 11 operator applications spanning eight distinct operator types, producing 16 changed-file events and seven new files. Maximum within-case token-set Jaccard overlap ranged from 0.000 to 0.478, with a mean of 0.274.

Each case was run once and was used during development. The results therefore show executable behavior and regression coverage, not statistical variance, held-out performance, or independent factual validation.

## Reproduce

With Ollama running locally:

```bash
ollama pull qwen3.6
python3 manager.py examples/es_input.md --memory work/cold-start --model qwen3.6
python3 benchmark.py --model qwen3.6 --report work/benchmark-report.json
```

If the local Ollama tag differs, pass it with `--model` or set `THREEM_MODEL`.
