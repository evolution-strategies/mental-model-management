import json
import tempfile
import unittest
from pathlib import Path

from three_m.contracts import validate_markdown_writes, validate_operator_contract
from three_m.manager import Manager
from three_m.mock import MockGenerator
from three_m.prompts import OPERATORS, PROMPT_FILES
from three_m.store import MarkdownStore, StoreError


ROOT = Path(__file__).resolve().parents[1]


class ControllerGenerator(MockGenerator):
    def __init__(self, operations):
        super().__init__()
        self.operations = operations

    def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        if "3M CONTROLLER" in prompt:
            self.prompts.append(prompt)
            return json.dumps({"operations": self.operations, "rationale": "test"})
        return super().generate(prompt, json_mode=json_mode)


class RepairingGenerator(MockGenerator):
    def __init__(self):
        super().__init__()
        self.bad_add_sent = False

    def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        if prompt.startswith("# Operator: Add") and not self.bad_add_sent:
            self.bad_add_sent = True
            self.prompts.append(prompt)
            return json.dumps({
                "summary": "bad first attempt",
                "writes": {"concept.md": "# Invalid"},
            })
        return super().generate(prompt, json_mode=json_mode)


class ThreeMTests(unittest.TestCase):
    def test_every_operator_has_prompt(self):
        self.assertEqual(set(OPERATORS), set(PROMPT_FILES))
        for filename in PROMPT_FILES.values():
            self.assertTrue((ROOT / "prompts" / filename).is_file(), filename)

    def test_store_rejects_unsafe_names(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MarkdownStore(Path(directory))
            with self.assertRaises(StoreError):
                store.write_atomic("../escape.md", "# No")

    def test_store_backs_up_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MarkdownStore(Path(directory))
            store.write_atomic("model.md", "# First")
            store.write_atomic("model.md", "# Second")
            self.assertEqual(store.read("model.md"), "# Second\n")
            self.assertEqual(len(list((Path(directory) / ".backups").glob("*.md"))), 1)

    def test_mock_pipeline_is_sequential_and_dry_run_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MarkdownStore(Path(directory))
            generator = MockGenerator()
            manager = Manager(store, ROOT / "prompts", generator)
            report = manager.process(
                "Mutation strength follows success rate.",
                source_name="examples/es_input.md",
                dry_run=True,
            )
            self.assertEqual(report["pipeline"], ["Extract", "Retrieve", "Add", "Verify"])
            self.assertEqual(report["verification"]["status"], "pass")
            self.assertIn("success-based-adaptation.md", report["changes"])
            self.assertEqual(store.list_names(), [])
            controller_prompt = next(prompt for prompt in generator.prompts if "3M CONTROLLER" in prompt)
            self.assertIn("Success-Based Adaptation", controller_prompt)

    def test_long_cold_start_creates_multiple_focused_models_and_preserves_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = Manager(MarkdownStore(Path(directory)), ROOT / "prompts", MockGenerator())
            long_input = "population covariance mutation adaptation " * 100
            report = manager.process(long_input, dry_run=True)
            self.assertEqual(
                set(report["changes"]),
                {
                    "success-based-adaptation.md",
                    "mutation-strength.md",
                    "covariance-adaptation.md",
                },
            )

    def test_verification_block_prevents_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MarkdownStore(Path(directory))
            manager = Manager(store, ROOT / "prompts", MockGenerator(verification_status="block"))
            report = manager.process("Mutation strength follows success rate.")
            self.assertEqual(report["commit_status"], "blocked")
            self.assertEqual(store.list_names(), [])

    def test_invalid_operator_output_gets_bounded_contract_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            generator = RepairingGenerator()
            manager = Manager(MarkdownStore(Path(directory)), ROOT / "prompts", generator)
            report = manager.process("Mutation strength follows success rate.", dry_run=True)
            self.assertIn("success-based-adaptation.md", report["changes"])
            repaired_prompt = [p for p in generator.prompts if p.startswith("# Operator: Add")][-1]
            self.assertIn("PREVIOUS RESPONSE WAS REJECTED", repaired_prompt)

    def test_later_transform_receives_newly_staged_file(self):
        with tempfile.TemporaryDirectory() as directory:
            generator = ControllerGenerator(["Add", "Connect"])
            manager = Manager(MarkdownStore(Path(directory)), ROOT / "prompts", generator)
            manager.process("Mutation strength follows success rate.", dry_run=True)
            connect_prompt = next(
                prompt for prompt in generator.prompts if prompt.startswith("# Operator: Connect")
            )
            self.assertIn("FILE: success-based-adaptation.md", connect_prompt)

    def test_controller_operation_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            operations = ["Add", "Update", "Connect", "Compress", "Infer", "Generalize"]
            manager = Manager(
                MarkdownStore(Path(directory)),
                ROOT / "prompts",
                ControllerGenerator(operations),
                max_operations=5,
            )
            with self.assertRaisesRegex(ValueError, "maximum is 5"):
                manager.process("input")

    def test_conflict_detection_is_inserted_before_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MarkdownStore(Path(directory))
            store.write_atomic("existing.md", "# Mental Model: Existing")
            manager = Manager(
                store,
                ROOT / "prompts",
                ControllerGenerator(["Conflict Repair"]),
            )
            # The mock operators make no writes, but the reported decision still
            # exposes the manager-normalized, safe ordering.
            report = manager.process("input", dry_run=True)
            self.assertEqual(
                report["decision"]["operations"],
                ["Conflict Detection", "Conflict Repair"],
            )

    def test_generic_and_title_mismatched_filenames_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Generic filename"):
            validate_markdown_writes(
                {"concept.md": "# Mental Model: Useful Concept"}, max_words=1500
            )
        with self.assertRaisesRegex(ValueError, "expected 'useful-concept.md'"):
            validate_markdown_writes(
                {"wrong-name.md": "# Mental Model: Useful Concept"}, max_words=1500
            )
        with self.assertRaisesRegex(ValueError, "must begin"):
            validate_markdown_writes(
                {
                    "useful-concept.md": (
                        "Status: Superseded\n\n# Mental Model: Useful Concept"
                    )
                },
                max_words=1500,
            )

    def test_one_concept_and_word_limit_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "one primary concept"):
            validate_markdown_writes(
                {"useful-concept.md": "# Mental Model: Useful Concept\n# Other"}, max_words=1500
            )
        body = "# Mental Model: Useful Concept\n\n" + "word " * 20
        with self.assertRaisesRegex(ValueError, "use Split"):
            validate_markdown_writes({"useful-concept.md": body}, max_words=10)

    def test_infer_contract_requires_premises_and_derived_knowledge(self):
        writes = validate_markdown_writes(
            {"useful-concept.md": "# Mental Model: Useful Concept\n\n## Premises\n- A"},
            max_words=1500,
        )
        with self.assertRaisesRegex(ValueError, "Derived Knowledge"):
            validate_operator_contract("Infer", {"writes": writes}, writes)

    def test_connect_contract_requires_relations(self):
        writes = validate_markdown_writes(
            {"useful-concept.md": "# Mental Model: Useful Concept\n\n## Description\n- A"},
            max_words=1500,
        )
        with self.assertRaisesRegex(ValueError, "Relations"):
            validate_operator_contract("Connect", {"writes": writes}, writes)

    def test_abstract_contract_requires_instances(self):
        writes = validate_markdown_writes(
            {"higher-level.md": "# Mental Model: Higher Level\n\n## Description\n- Shared structure"},
            max_words=1500,
        )
        with self.assertRaisesRegex(ValueError, "Instances"):
            validate_operator_contract("Abstract", {"writes": writes}, writes)

    def test_merge_contract_requires_superseded_source_rewrites(self):
        writes = validate_markdown_writes(
            {
                "step-size.md": "# Mental Model: Step Size\n\n## Chunks\n- Canonical.",
                "mutation-scale.md": (
                    "# Mental Model: Mutation Scale\n\n"
                    "Status: Superseded by [Step Size](step-size.md)"
                ),
            },
            max_words=1500,
        )
        result = {
            "metadata": {
                "canonical_file": "step-size.md",
                "merged_sources": ["step-size.md", "mutation-scale.md"],
                "supersedes": ["mutation-scale.md"],
            }
        }
        validate_operator_contract("Merge", result, writes)

    def test_superseded_title_suffix_keeps_stable_semantic_filename(self):
        writes = validate_markdown_writes(
            {
                "mutation-scale.md": (
                    "# Mental Model: Mutation Scale (Superseded)\n\n"
                    "Status: Superseded by [Step Size](step-size.md)"
                )
            },
            max_words=1500,
        )
        self.assertIn("mutation-scale.md", writes)


if __name__ == "__main__":
    unittest.main()
