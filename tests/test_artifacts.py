import json
import unittest
from pathlib import Path

from aurevion_knowledge_lab.artifacts import evaluation_rows, example_graph, impacted_decisions

ROOT = Path(__file__).resolve().parents[1]


class ArtifactTests(unittest.TestCase):
    def test_unknown_paper_cannot_become_a_traceable_link(self):
        annotations = {"claims": [{"id": "c", "title": "Draft", "population": "Adults", "source_ids": ["missing"], "status": "draft", "note": ""}], "decisions": []}
        with self.assertRaisesRegex(ValueError, "Unknown paper"):
            example_graph([], annotations)

    def test_unknown_claim_cannot_inform_a_decision(self):
        annotations = {"claims": [], "decisions": [{"id": "d", "title": "Decision", "claim_ids": ["missing"], "status": "draft", "rationale": ""}]}
        with self.assertRaisesRegex(ValueError, "Unknown claim"):
            example_graph([], annotations)

    def test_evaluations_do_not_claim_scores_before_review(self):
        row = evaluation_rows([{"id": "q", "required_source_ids": ["absent"]}], {"present"})[0]
        self.assertFalse(row["corpus_covered"])
        self.assertIsNone(row["citation_accuracy"])
        self.assertIsNone(row["unsupported_claims"])

    def test_demo_is_explicitly_human_authored(self):
        manifest = [json.loads(line) for line in (ROOT / "corpus/manifest.jsonl").read_text().splitlines() if line.strip()]
        annotations = json.loads((ROOT / "decisions/examples.json").read_text())
        graph = example_graph(manifest, annotations)
        self.assertEqual(graph["status"], "human_authored_draft_examples")
        self.assertTrue(all(node["status"] != "reviewed" for node in graph["nodes"]))

    def test_impact_tracking_uses_explicit_evidence_paths(self):
        manifest = [json.loads(line) for line in (ROOT / "corpus/manifest.jsonl").read_text().splitlines() if line.strip()]
        annotations = json.loads((ROOT / "decisions/examples.json").read_text())
        rows = impacted_decisions(example_graph(manifest, annotations), "PMC3879660")
        self.assertEqual([row["decision_id"] for row in rows], ["decision:nutrition-explanations"])
        self.assertEqual(rows[0]["source_path"], ["PMC3879660", "claim:protein-context", "decision:nutrition-explanations"])

    def test_full_text_question_is_not_covered_by_abstracts(self):
        row = evaluation_rows([{"id": "q", "required_source_ids": ["paper"], "minimum_document_mode": "full_text"}], {"paper"})[0]
        self.assertTrue(row["corpus_covered"])
        self.assertFalse(row["mode_covered"])


if __name__ == "__main__":
    unittest.main()
