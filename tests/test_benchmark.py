import unittest
from pathlib import Path

from three_m.benchmark import evaluate_case, load_cases, maximum_pairwise_jaccard


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    def test_all_benchmark_cases_load(self):
        cases = load_cases(ROOT / "benchmarks" / "cases")
        self.assertEqual(len(cases), 6)
        self.assertEqual(len({data["id"] for _, data in cases}), 6)
        for case_dir, data in cases:
            self.assertTrue((case_dir / "input.md").is_file(), data["id"])
            self.assertIn("manual_review", data)

    def test_pairwise_redundancy_ignores_superseded_files(self):
        memory = {
            "alpha.md": "# Mental Model: Alpha\n- mutation scale controls search",
            "beta.md": "# Mental Model: Beta\n- mutation scale controls search",
            "old.md": (
                "# Mental Model: Old (Superseded)\n"
                "Status: Superseded by [Alpha](alpha.md)\n"
                "- mutation scale controls search"
            ),
        }
        score, pair = maximum_pairwise_jaccard(memory)
        self.assertGreater(score, 0.5)
        self.assertNotIn("old.md", pair)

    def test_evaluator_accepts_behavior_not_exact_wording(self):
        spec = {
            "id": "synthetic",
            "title": "Synthetic",
            "expected": {
                "required_operations_all": ["Add"],
                "min_changes": 1,
                "max_changes": 2,
                "min_new_files": 1,
                "max_new_files": 2,
                "required_headings_any": ["Knowledge Gaps"],
                "required_headings_each_new": ["Provenance"],
                "required_terms_anywhere": ["mutation"],
                "max_pairwise_jaccard": 1.0,
                "verification_status": ["pass"],
            },
        }
        report = {
            "decision": {"operations": ["Add"]},
            "pipeline": ["Extract", "Retrieve", "Add", "Verify"],
            "changes": ["mutation.md"],
            "commit_status": "committed",
            "verification": {"status": "pass"},
        }
        after = {
            "mutation.md": (
                "# Mental Model: Mutation\n\n## Knowledge Gaps\n- How?\n\n"
                "## Provenance\n- Source"
            )
        }
        result = evaluate_case(spec, report, {}, after)
        self.assertTrue(result["passed"], result["checks"])


if __name__ == "__main__":
    unittest.main()

