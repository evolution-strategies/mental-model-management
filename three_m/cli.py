"""CLI wiring for the 3M manager."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .manager import Manager
from .mock import MockGenerator
from .ollama import OllamaClient, OllamaError
from .store import MarkdownStore


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Manage persistent Markdown mental models with 3M operators.")
    result.add_argument("input", type=Path, help="UTF-8 text or Markdown input")
    result.add_argument("--memory", type=Path, default=Path("memory"), help="Markdown memory directory")
    result.add_argument("--prompts", type=Path, default=Path("prompts"), help="operator prompt directory")
    result.add_argument("--model", default=os.getenv("THREEM_MODEL", "qwen3.6"))
    result.add_argument("--host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    result.add_argument("--mock", action="store_true", help="use deterministic offline responses")
    result.add_argument("--dry-run", action="store_true", help="show proposed changes without writing memory")
    result.add_argument("--max-operations", type=int, default=5, help="maximum transformations per input")
    result.add_argument("--max-model-words", type=int, default=1500, help="maximum words per mental model")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    generator = MockGenerator() if args.mock else OllamaClient(args.model, args.host)
    manager = Manager(
        MarkdownStore(args.memory),
        args.prompts,
        generator,
        max_operations=args.max_operations,
        max_model_words=args.max_model_words,
    )
    try:
        report = manager.process(
            args.input.read_text(encoding="utf-8"),
            source_name=str(args.input),
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, OllamaError) as exc:
        print(f"error: {exc}")
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0
