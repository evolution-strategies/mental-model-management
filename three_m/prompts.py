"""Prompt loading and canonical operator names."""

from pathlib import Path

OPERATORS = (
    "Extract", "Retrieve", "Add", "Update", "Merge", "Split", "Connect",
    "Conflict Detection", "Conflict Repair", "Compress", "Generalize",
    "Specialize", "Infer", "Analogy", "Find Gap", "Verify", "Prune", "Abstract",
)

PROMPT_FILES = {name: name.lower().replace(" ", "_") + ".md" for name in OPERATORS}


def load_prompt(directory: Path, operator: str) -> str:
    if operator not in PROMPT_FILES:
        raise ValueError(f"Unknown operator: {operator}")
    return (directory / PROMPT_FILES[operator]).read_text(encoding="utf-8")

