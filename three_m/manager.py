"""The single-process, contract-checked 3M controller and execution loop."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .contracts import validate_markdown_writes, validate_operator_contract, validate_verification
from .prompts import OPERATORS, load_prompt
from .store import MarkdownStore

MANDATORY_OPERATORS = {"Extract", "Retrieve", "Verify"}
TRANSFORM_OPERATORS = tuple(name for name in OPERATORS if name not in MANDATORY_OPERATORS)


class Generator(Protocol):
    def generate(self, prompt: str, *, json_mode: bool = False) -> str: ...


@dataclass
class Decision:
    operations: list[str]
    relevant_files: list[str]
    rationale: str = ""


class Manager:
    def __init__(
        self,
        store: MarkdownStore,
        prompts: Path,
        generator: Generator,
        *,
        max_operations: int = 5,
        max_model_words: int = 1500,
        max_initial_models: int = 7,
    ):
        self.store = store
        self.prompts = prompts
        self.generator = generator
        self.max_operations = max_operations
        self.max_model_words = max_model_words
        self.max_initial_models = max_initial_models

    def process(self, input_text: str, *, source_name: str = "input", dry_run: bool = False) -> dict:
        inventory = self.store.snapshot()
        working = dict(inventory)
        trace: list[dict] = []
        context: list[dict] = []

        extraction = self._call_operator(
            "Extract", input_text, source_name, inventory, context, allowed_files=set()
        )
        candidates = self._validate_extraction(extraction)
        trace.append(self._trace("Extract", extraction, {}))
        context.append({"operator": "Extract", "summary": extraction.get("summary", ""), "candidates": candidates})

        retrieval = self._call_operator(
            "Retrieve", input_text, source_name, inventory, context, allowed_files=set()
        )
        relevant = self._validate_retrieval(retrieval, inventory)
        trace.append(self._trace("Retrieve", retrieval, {}))
        context.append({"operator": "Retrieve", "summary": retrieval.get("summary", ""), "relevant_files": relevant})

        decision = self._choose(input_text, source_name, inventory, context, relevant)
        active_names = set(relevant)
        cold_start_min_files = self._cold_start_min_files(input_text, candidates, inventory)
        preserve_gaps = not inventory and bool(candidates.get("gaps"))

        for operator in decision.operations:
            selected = {name: working[name] for name in sorted(active_names) if name in working}
            result = self._call_operator(
                operator,
                input_text,
                source_name,
                selected,
                context,
                allowed_files=None,
                validate_writes=True,
                min_add_files=cold_start_min_files if operator == "Add" else 0,
                require_knowledge_gaps=preserve_gaps if operator == "Add" else False,
            )
            writes = self._validated_writes(
                operator,
                result,
                min_add_files=cold_start_min_files if operator == "Add" else 0,
                require_knowledge_gaps=preserve_gaps if operator == "Add" else False,
            )
            working.update(writes)
            active_names.update(writes)
            trace.append(self._trace(operator, result, writes))
            context.append({
                "operator": operator,
                "summary": result.get("summary", ""),
                "metadata": result.get("metadata", {}),
                "staged_files": sorted(writes),
            })

        staged = {name: body for name, body in working.items() if inventory.get(name) != body}
        verification_status = "not_needed"
        verification_issues: list[str] = []
        if staged:
            verify_memory = {
                name: working[name]
                for name in sorted(active_names | set(staged))
                if name in working
            }
            verification = self._call_operator(
                "Verify",
                input_text,
                source_name,
                verify_memory,
                context,
                allowed_files=set(staged),
                verification_names=set(staged),
                validate_writes=True,
            )
            verification_status, verification_issues = validate_verification(verification, set(staged))
            corrections = self._validated_writes("Verify", verification)
            working.update(corrections)
            trace.append(self._trace("Verify", verification, corrections))
            context.append({
                "operator": "Verify",
                "summary": verification.get("summary", ""),
                "status": verification_status,
                "issues": verification_issues,
            })
            staged = {name: body for name, body in working.items() if inventory.get(name) != body}

        blocked = verification_status == "block"
        if not dry_run and not blocked:
            for name, body in staged.items():
                self.store.write_atomic(name, body)

        return {
            "decision": decision.__dict__,
            "pipeline": [item["operator"] for item in trace],
            "changes": sorted(staged),
            "commit_status": "blocked" if blocked else ("dry_run" if dry_run else "committed"),
            "verification": {"status": verification_status, "issues": verification_issues},
            "trace": trace,
        }

    def _choose(
        self,
        input_text: str,
        source_name: str,
        memory: dict[str, str],
        context: list[dict],
        relevant: list[str],
    ) -> Decision:
        template = (self.prompts / "controller.md").read_text(encoding="utf-8")
        prompt = template.format(
            operators=json.dumps(TRANSFORM_OPERATORS),
            max_operations=self.max_operations,
            source=source_name,
            input=input_text,
            context=json.dumps(context, ensure_ascii=False, indent=2),
            memory=self._render_memory({name: memory[name] for name in relevant}),
        )
        data = self._parse_json(self.generator.generate(prompt, json_mode=True))
        operations = data.get("operations", [])
        if not isinstance(operations, list) or not all(isinstance(name, str) for name in operations):
            raise ValueError("Controller operations must be a list of names")
        unknown = [name for name in operations if name not in TRANSFORM_OPERATORS]
        if unknown:
            raise ValueError(f"Controller selected unavailable transformations: {unknown}")
        if not memory and "Add" not in operations:
            operations.insert(0, "Add")
        if "Conflict Repair" in operations and (
            "Conflict Detection" not in operations
            or operations.index("Conflict Detection") > operations.index("Conflict Repair")
        ):
            repair_index = operations.index("Conflict Repair")
            if "Conflict Detection" in operations:
                operations.remove("Conflict Detection")
                repair_index = operations.index("Conflict Repair")
            operations.insert(repair_index, "Conflict Detection")
        if len(operations) > self.max_operations:
            raise ValueError(f"Controller selected {len(operations)} operations; maximum is {self.max_operations}")
        return Decision(operations=operations, relevant_files=relevant, rationale=data.get("rationale", ""))

    def _call_operator(
        self,
        operator: str,
        input_text: str,
        source_name: str,
        memory: dict[str, str],
        context: list[dict],
        *,
        allowed_files: set[str] | None,
        verification_names: set[str] | None = None,
        validate_writes: bool = False,
        min_add_files: int = 0,
        require_knowledge_gaps: bool = False,
    ) -> dict:
        template = load_prompt(self.prompts, operator)
        base = template.format(input=input_text, memory=self._render_memory(memory))
        constraints = (
            "\n\nRUNTIME CONTEXT (transient, never persist this JSON verbatim):\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
            + f"\n\nSOURCE LABEL: {source_name}\n"
            + f"MODEL LIMIT: one primary concept and at most {self.max_model_words} words per file.\n"
            + "FILENAMES: semantic lowercase slugs matching '# Mental Model: Title'; never concept.md, canonical.md, model.md, memory.md, or output.md.\n"
        )
        if operator == "Add" and min_add_files:
            constraints += (
                f"COLD START: create {min_add_files} to {self.max_initial_models} focused new mental-model files. "
                "Do not collapse independently useful extracted concepts into one comprehensive file.\n"
            )
        if operator == "Add" and require_knowledge_gaps:
            constraints += "PRESERVE GAPS: at least one written file must contain a non-empty '## Knowledge Gaps' section.\n"
        if verification_names is not None:
            constraints += "STAGED FILES VERIFY MAY CORRECT: " + json.dumps(sorted(verification_names)) + "\n"
        prompt = base + constraints
        last_error: ValueError | None = None
        # Structured local models occasionally repeat a formatting mistake once;
        # allow two bounded repair attempts before rejecting the whole batch.
        for attempt in range(3):
            raw = self.generator.generate(prompt, json_mode=True)
            try:
                result = self._parse_json(raw)
                writes = result.get("writes", {})
                if allowed_files == set() and writes:
                    raise ValueError(f"{operator} is transient and must return no writes")
                if allowed_files is not None and set(writes) - allowed_files:
                    raise ValueError(f"{operator} attempted writes outside {sorted(allowed_files)}")
                if validate_writes:
                    self._validated_writes(
                        operator,
                        result,
                        min_add_files=min_add_files,
                        require_knowledge_gaps=require_knowledge_gaps,
                    )
                if verification_names is not None:
                    validate_verification(result, verification_names)
                return result
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = ValueError(str(exc))
                if attempt < 2:
                    prompt += f"\n\nYOUR PREVIOUS RESPONSE WAS REJECTED: {exc}\nReturn corrected JSON only.\n"
        raise last_error or ValueError(f"{operator} failed")

    def _validated_writes(
        self,
        operator: str,
        result: dict,
        *,
        min_add_files: int = 0,
        require_knowledge_gaps: bool = False,
    ) -> dict[str, str]:
        writes = validate_markdown_writes(result.get("writes", {}), max_words=self.max_model_words)
        validate_operator_contract(operator, result, writes)
        if operator == "Add" and min_add_files:
            if not min_add_files <= len(writes) <= self.max_initial_models:
                raise ValueError(
                    f"Cold-start Add must create {min_add_files} to {self.max_initial_models} focused files; "
                    f"received {len(writes)}"
                )
        if operator == "Add" and require_knowledge_gaps:
            has_gaps = any(
                re.search(r"^##\s+Knowledge Gaps\s*$", body, re.MULTILINE | re.IGNORECASE)
                for body in writes.values()
            )
            if not has_gaps:
                raise ValueError("Cold-start Add must preserve extracted questions under '## Knowledge Gaps'")
        return writes

    @staticmethod
    def _cold_start_min_files(input_text: str, candidates: dict, inventory: dict[str, str]) -> int:
        if inventory:
            return 0
        concepts = [item for item in candidates.get("concepts", []) if isinstance(item, str) and item.strip()]
        word_count = len(re.findall(r"\b[\w'-]+\b", input_text, re.UNICODE))
        if word_count >= 400 and len(concepts) >= 3:
            return 3
        return 1

    @staticmethod
    def _validate_extraction(result: dict) -> dict:
        candidates = result.get("candidates")
        if not isinstance(candidates, dict):
            raise ValueError("Extract must return a transient 'candidates' object")
        for key in ("concepts", "claims", "relations", "gaps"):
            if not isinstance(candidates.get(key), list):
                raise ValueError(f"Extract candidates.{key} must be a list")
        return candidates

    @staticmethod
    def _validate_retrieval(result: dict, memory: dict[str, str]) -> list[str]:
        files = result.get("relevant_files")
        if not isinstance(files, list) or not all(isinstance(name, str) for name in files):
            raise ValueError("Retrieve must return relevant_files as a list")
        unknown = set(files) - set(memory)
        if unknown:
            raise ValueError(f"Retrieve named missing files: {sorted(unknown)}")
        return list(dict.fromkeys(files))

    @staticmethod
    def _trace(operator: str, result: dict, writes: dict[str, str]) -> dict:
        item = {"operator": operator, "summary": result.get("summary", ""), "writes": sorted(writes)}
        if "verification" in result:
            item["verification"] = result["verification"]
        return item

    @staticmethod
    def _render_memory(memory: dict[str, str]) -> str:
        if not memory:
            return "(empty memory)"
        return "\n\n".join(f"FILE: {name}\n{body}" for name, body in memory.items())

    @staticmethod
    def _parse_json(raw: str) -> dict:
        raw = raw.strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError("Model did not return a JSON object")
            value = json.loads(match.group(0))
        if not isinstance(value, dict):
            raise ValueError("Model response must be a JSON object")
        return value
