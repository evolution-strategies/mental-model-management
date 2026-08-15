"""Deterministic contracts around model-proposed Markdown transformations."""

from __future__ import annotations

import re
import unicodedata

from .store import StoreError

GENERIC_STEMS = {"canonical", "concept", "memory", "mental-model", "model", "output"}
MENTAL_MODEL_TITLE = re.compile(r"^# Mental Model:\s*(.+?)\s*$", re.MULTILINE)


def slugify(value: str) -> str:
    # A merge may annotate the old model's title while keeping its stable,
    # concept-derived filename and an explicit Superseded by status in the body.
    value = re.sub(r"\s*[\[(]superseded[\])]\s*$", "", value, flags=re.IGNORECASE)
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def validate_markdown_writes(writes: object, *, max_words: int) -> dict[str, str]:
    if not isinstance(writes, dict):
        raise ValueError("Operator response 'writes' must be an object")
    clean: dict[str, str] = {}
    for name, body in writes.items():
        if not isinstance(name, str) or not isinstance(body, str):
            raise ValueError("Every write must map a filename to Markdown text")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*\.md", name):
            raise StoreError(f"Unsafe filename: {name!r}")
        stem = name.removesuffix(".md")
        if stem in GENERIC_STEMS:
            raise ValueError(f"Generic filename {name!r} is not allowed; name the concept")
        if not body.lstrip().startswith("# Mental Model:"):
            raise ValueError(f"{name}: Markdown must begin with '# Mental Model: …'")
        titles = MENTAL_MODEL_TITLE.findall(body)
        if len(titles) != 1:
            raise ValueError(f"{name}: require exactly one '# Mental Model: …' heading")
        expected = slugify(titles[0]) + ".md"
        if name != expected:
            raise ValueError(f"{name}: filename must match its title; expected {expected!r}")
        h1_count = len(re.findall(r"^#\s+", body, re.MULTILINE))
        if h1_count != 1:
            raise ValueError(f"{name}: require one primary concept and one level-1 heading")
        words = len(re.findall(r"\b[\w'-]+\b", body, re.UNICODE))
        if words > max_words:
            raise ValueError(
                f"{name}: {words} words exceeds the {max_words}-word concept limit; use Split"
            )
        clean[name] = body.strip() + "\n"
    return clean


def require_heading(writes: dict[str, str], heading: str, operator: str) -> None:
    for name, body in writes.items():
        if not re.search(rf"^##\s+{re.escape(heading)}\s*$", body, re.MULTILINE | re.IGNORECASE):
            raise ValueError(f"{operator}: {name} must contain '## {heading}'")


def validate_operator_contract(operator: str, result: dict, writes: dict[str, str]) -> None:
    if operator == "Add":
        require_heading(writes, "Provenance", operator)
    elif operator == "Infer":
        require_heading(writes, "Premises", operator)
        require_heading(writes, "Derived Knowledge", operator)
    elif operator == "Generalize":
        require_heading(writes, "Supporting Observations", operator)
        require_heading(writes, "Derived Knowledge", operator)
    elif operator == "Find Gap":
        require_heading(writes, "Knowledge Gaps", operator)
    elif operator == "Connect":
        require_heading(writes, "Relations", operator)
    elif operator == "Abstract":
        require_heading(writes, "Instances", operator)
    elif operator == "Conflict Repair":
        require_heading(writes, "Repair Audit", operator)
    elif operator == "Merge":
        _validate_merge(result, writes)


def _validate_merge(result: dict, writes: dict[str, str]) -> None:
    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Merge must return transient 'metadata'")
    canonical = metadata.get("canonical_file")
    sources = metadata.get("merged_sources")
    supersedes = metadata.get("supersedes")
    if not isinstance(canonical, str) or canonical not in writes:
        raise ValueError("Merge canonical_file must be present in writes")
    if not isinstance(sources, list) or len(sources) < 2 or not all(isinstance(x, str) for x in sources):
        raise ValueError("Merge merged_sources must name at least two files")
    if not isinstance(supersedes, list) or not all(isinstance(x, str) for x in supersedes):
        raise ValueError("Merge supersedes must be a filename list")
    expected = set(sources) - {canonical}
    if set(supersedes) != expected:
        raise ValueError("Merge supersedes must contain every non-canonical merged source")
    for name in supersedes:
        if name not in writes or "superseded by" not in writes[name].lower():
            raise ValueError(f"Merge must rewrite {name} with an explicit 'Superseded by' status")


def validate_verification(result: dict, staged_names: set[str]) -> tuple[str, list[str]]:
    verification = result.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("Verify must return a 'verification' object")
    status = verification.get("status")
    issues = verification.get("issues", [])
    if status not in {"pass", "corrected", "block"}:
        raise ValueError("Verify status must be pass, corrected, or block")
    if not isinstance(issues, list) or not all(isinstance(item, str) for item in issues):
        raise ValueError("Verify issues must be a list of strings")
    writes = result.get("writes", {})
    if not isinstance(writes, dict):
        raise ValueError("Verify writes must be an object")
    unexpected = set(writes) - staged_names
    if unexpected:
        raise ValueError(f"Verify may only correct staged files, not create {sorted(unexpected)}")
    if status == "corrected" and issues and not writes:
        raise ValueError("Verify reported corrections but returned no corrected files")
    return status, issues
