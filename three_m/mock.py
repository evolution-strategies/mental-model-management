"""Deterministic offline generator for smoke tests and demonstrations."""

from __future__ import annotations

import json
import re


class MockGenerator:
    def __init__(self, *, verification_status: str = "pass"):
        self.verification_status = verification_status
        self.prompts: list[str] = []

    def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        self.prompts.append(prompt)
        operator = re.search(r"^# Operator: (.+)$", prompt, re.MULTILINE)
        name = operator.group(1) if operator else ""
        if name == "Extract":
            return json.dumps({
                "summary": "Found success-based adaptation knowledge.",
                "candidates": {
                    "concepts": [
                        "Evolution Strategy",
                        "Success-Based Adaptation",
                        "Mutation Strength",
                        "Covariance Adaptation",
                    ],
                    "claims": ["Observed success can guide mutation strength."],
                    "relations": ["Success Rate -> guides -> Mutation Strength"],
                    "gaps": ["What target success rate should be used?"],
                },
                "writes": {},
            })
        if name == "Retrieve":
            files = re.findall(r"^FILE: ([a-z0-9_-]+\.md)$", prompt, re.MULTILINE)
            return json.dumps({"summary": "Retrieved related ES models.", "relevant_files": files, "writes": {}})
        if "3M CONTROLLER" in prompt:
            return json.dumps({
                "operations": ["Add"],
                "rationale": "Add the new concept; final verification is enforced by the manager.",
            })
        if name == "Add":
            bodies = {"success-based-adaptation.md": """# Mental Model: Success-Based Adaptation

## Description

Adapts mutation strength using observed search success.

## Chunks

- Search success provides feedback for adapting mutation strength.
- High success can indicate that larger steps are useful.
- Low success can indicate that smaller steps are useful.

## Knowledge Gaps

- Which target success rate should be used?

## Provenance

- Source: examples/es_input.md
"""}
            minimum = re.search(r"COLD START: create (\d+) to", prompt)
            if minimum and int(minimum.group(1)) >= 2:
                bodies["mutation-strength.md"] = """# Mental Model: Mutation Strength

## Description

Controls mutation scale in an Evolution Strategy.

## Chunks

- Larger values produce broader mutations.
- Smaller values support local refinement.

## Provenance

- Source: examples/es_long_input.md
"""
                bodies["covariance-adaptation.md"] = """# Mental Model: Covariance Adaptation

## Description

Adapts the directional structure of a search distribution.

## Chunks

- A covariance matrix can represent scale and orientation.

## Provenance

- Source: examples/es_long_input.md
"""
            return json.dumps({"summary": "Added focused concept models.", "writes": bodies})
        if name == "Verify":
            issues = ["Mock verification block."] if self.verification_status == "block" else []
            return json.dumps({
                "summary": "Checked staged claims against the supplied source and memory.",
                "verification": {"status": self.verification_status, "issues": issues},
                "writes": {},
            })
        return json.dumps({"summary": f"Mock {name}: no persistent change.", "writes": {}})
