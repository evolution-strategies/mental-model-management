"""Dependency-free benchmark runner for Mental Model Management."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .manager import Manager
from .ollama import OllamaClient, OllamaError
from .store import MarkdownStore


def load_cases(root: Path, selected: list[str] | None = None) -> list[tuple[Path, dict]]:
    wanted = set(selected or [])
    cases = []
    for case_file in sorted(root.glob("*/case.json")):
        data = json.loads(case_file.read_text(encoding="utf-8"))
        if not wanted or data["id"] in wanted:
            cases.append((case_file.parent, data))
    missing = wanted - {data["id"] for _, data in cases}
    if missing:
        raise ValueError(f"Unknown benchmark cases: {sorted(missing)}")
    return cases


def tokenize(markdown: str) -> set[str]:
    stop = {"about", "after", "also", "and", "are", "from", "into", "that", "the", "their", "this", "with"}
    return {
        token
        for token in re.findall(r"[a-z][a-z0-9-]{2,}", markdown.lower())
        if token not in stop
    }


def maximum_pairwise_jaccard(memory: dict[str, str]) -> tuple[float, list[str]]:
    active = {
        name: tokenize(body)
        for name, body in memory.items()
        if "status: superseded by" not in body.lower()
    }
    maximum = 0.0
    pair: list[str] = []
    names = sorted(active)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            union = active[left] | active[right]
            score = len(active[left] & active[right]) / len(union) if union else 0.0
            if score > maximum:
                maximum, pair = score, [left, right]
    return maximum, pair


def evaluate_case(
    spec: dict,
    report: dict,
    before: dict[str, str],
    after: dict[str, str],
) -> dict:
    expected = spec.get("expected", {})
    operations = report.get("decision", {}).get("operations", [])
    changed = report.get("changes", [])
    new_files = sorted(set(after) - set(before))
    changed_bodies = "\n".join(after[name] for name in changed if name in after)
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    pipeline = report.get("pipeline", [])
    check("pipeline-prefix", pipeline[:2] == ["Extract", "Retrieve"], str(pipeline))
    if changed:
        check("verification-gate", bool(pipeline) and pipeline[-1] == "Verify", str(pipeline))
    allowed_status = expected.get("verification_status", ["pass", "corrected"])
    status = report.get("verification", {}).get("status")
    check("verification-status", status in allowed_status, f"status={status}, allowed={allowed_status}")
    check("committed", report.get("commit_status") == "committed", report.get("commit_status", "missing"))

    required_all = expected.get("required_operations_all", [])
    check("required-operations-all", all(item in operations for item in required_all), f"actual={operations}")
    required_any = expected.get("required_operations_any", [])
    if required_any:
        check("required-operations-any", any(item in operations for item in required_any), f"actual={operations}")
    forbidden = expected.get("forbidden_operations", [])
    if forbidden:
        check("forbidden-operations", not any(item in operations for item in forbidden), f"actual={operations}")

    min_changes = expected.get("min_changes", 0)
    max_changes = expected.get("max_changes", 10_000)
    check("change-count", min_changes <= len(changed) <= max_changes, f"changed={len(changed)}")
    min_new = expected.get("min_new_files", 0)
    max_new = expected.get("max_new_files", 10_000)
    check("new-file-count", min_new <= len(new_files) <= max_new, f"new={new_files}")

    for heading in expected.get("required_headings_any", []):
        found = any(
            re.search(rf"^##\s+{re.escape(heading)}\s*$", after[name], re.MULTILINE | re.IGNORECASE)
            for name in changed
            if name in after
        )
        check(f"heading-any:{heading}", found, f"changed={changed}")
    for heading in expected.get("required_headings_each_new", []):
        missing = [
            name
            for name in new_files
            if not re.search(rf"^##\s+{re.escape(heading)}\s*$", after[name], re.MULTILINE | re.IGNORECASE)
        ]
        check(f"heading-each-new:{heading}", not missing, f"missing={missing}")

    for term in expected.get("required_terms_anywhere", []):
        check(f"term:{term}", term.lower() in changed_bodies.lower(), f"term={term!r}")

    max_allowed = float(expected.get("max_pairwise_jaccard", 1.0))
    similarity, pair = maximum_pairwise_jaccard(after)
    check("redundancy", similarity <= max_allowed, f"max={similarity:.3f}, pair={pair}, allowed={max_allowed:.3f}")

    required_files = expected.get("required_files", [])
    if required_files:
        check("required-files", all(name in after for name in required_files), f"actual={sorted(after)}")

    return {
        "id": spec["id"],
        "title": spec["title"],
        "dimensions": spec.get("dimensions", []),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "operations": operations,
        "changed_files": changed,
        "new_files": new_files,
        "manual_review": spec.get("manual_review", []),
    }


def run_case(
    case_dir: Path,
    spec: dict,
    *,
    generator: OllamaClient,
    prompts: Path,
    artifacts: Path | None,
) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"3m-{spec['id']}-") as temporary:
        memory_root = Path(temporary) / "memory"
        memory_root.mkdir()
        initial = case_dir / "initial_memory"
        if initial.is_dir():
            for source in initial.glob("*.md"):
                shutil.copy2(source, memory_root / source.name)
        store = MarkdownStore(memory_root)
        before = store.snapshot()
        manager = Manager(store, prompts, generator)
        report = manager.process(
            (case_dir / "input.md").read_text(encoding="utf-8"),
            source_name=f"benchmarks/cases/{spec['id']}/input.md",
        )
        after = store.snapshot()
        result = evaluate_case(spec, report, before, after)
        result["trace"] = report.get("trace", [])
        if artifacts is not None:
            target = artifacts / spec["id"]
            target.mkdir(parents=True, exist_ok=True)
            for name, body in after.items():
                (target / name).write_text(body, encoding="utf-8")
        return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Run the 3M behavioral benchmark.")
    result.add_argument("--cases", type=Path, default=Path("benchmarks/cases"))
    result.add_argument("--case", action="append", dest="selected", help="case id; repeat to select several")
    result.add_argument("--prompts", type=Path, default=Path("prompts"))
    result.add_argument("--model", default=os.getenv("THREEM_MODEL", "qwen3.6"))
    result.add_argument("--host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    result.add_argument("--report", type=Path, help="optional JSON report path")
    result.add_argument("--artifacts", type=Path, help="optional final Markdown memory directory")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        cases = load_cases(args.cases, args.selected)
        generator = OllamaClient(args.model, args.host)
        results = []
        for case_dir, spec in cases:
            try:
                results.append(
                    run_case(case_dir, spec, generator=generator, prompts=args.prompts, artifacts=args.artifacts)
                )
            except (OSError, ValueError, OllamaError) as exc:
                results.append({
                    "id": spec["id"],
                    "title": spec["title"],
                    "passed": False,
                    "error": str(exc),
                    "checks": [],
                    "manual_review": spec.get("manual_review", []),
                })
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2

    passed = sum(bool(item.get("passed")) for item in results)
    report = {
        "benchmark": "3M behavioral benchmark",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "summary": {"passed": passed, "total": len(results), "rate": passed / len(results) if results else 0.0},
        "cases": results,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if passed == len(results) else 1
