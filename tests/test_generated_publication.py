from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from hsdl_gap.generated_publication import (
    GeneratedPublicationError,
    build_generated_publication_preview,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "publication" / "model_relative_technical_preview_spec.json"
LEDGER = ROOT / "claims" / "model_relative_claims.json"
DECLARATION = ROOT / "governance" / "project_identity_declaration.json"


class GeneratedPublicationTests(unittest.TestCase):
    def _write_artifacts(self, root: Path) -> None:
        artifacts = {
            "model-relative-metric-analysis.json": {
                "metrics": [
                    {"numerator": 6, "denominator": 46, "measure_id": "UNWEIGHTED_CATALOG_ROW_SHARE"},
                    {"numerator": 40, "denominator": 46, "measure_id": "UNWEIGHTED_CATALOG_ROW_SHARE"},
                    {"numerator": 690, "denominator": 6440, "unknown_count": 5750},
                    {"numerator": 322, "denominator": 6440, "unknown_count": 5750, "value": None},
                ],
                "sensitivity": {
                    "changed_evaluation_count": 184,
                    "evaluation_count": 6440,
                    "classification": "ASSUMPTION_SENSITIVE",
                },
            },
            "source-derived-predicate-report.json": {
                "executable_predicate_count": 20,
                "readiness_only_predicate_count": 0,
                "duty_count": 25,
            },
            "eu-article6-context-v2-corpus.json": {
                "context_count": 36,
                "native_route_count": 9,
                "classification_state_counts": {"IN_SCOPE": 18, "OUT_OF_SCOPE": 9, "UNKNOWN": 9},
            },
            "decision33-eu-relation-scenarios.json": {
                "scenario_count": 2,
                "context_count_per_scenario": 322,
                "completeness": {"all_322_contexts_receive_scenario_metadata": True},
            },
            "operational-duty-signature-report.json": {
                "exact_cross_jurisdiction_pair_count": 0,
                "same_slot_cross_jurisdiction_pair_count": 0,
            },
            "independent-javascript-oracle-report.json": {
                "projection_hash_match": True,
                "projection_count": 12880,
                "implementation_boundary": {"shared_python_evaluator_code": False},
            },
            "source-derived-symbolic-profile-v2-report.json": {
                "symbolically_compiled_rule_count": 20,
                "candidate_rule_count": 20,
                "duty_trigger_expression_count": 5,
                "mismatch_count": 0,
            },
            "candidate-priority-report.json": {
                "edge_count": 9,
                "conditional_edge_count": 2,
                "source_evidenced_edge_count": 9,
                "limitations": {"cross_jurisdiction_priority": "NOT_DECLARED"},
            },
            "engineering-gate-status.json": {
                "p0": {"complete": True, "passed": 7},
                "status": "P0_COMPLETE_P1_CAPABILITIES_READY_COMPLETENESS_BLOCKED",
            },
        }
        for name, payload in artifacts.items():
            (root / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_preview_is_deterministic_and_contains_all_claims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            markdown = root / "preview.md"
            first = build_generated_publication_preview(
                spec_path=SPEC,
                ledger_path=LEDGER,
                artifact_dir=root,
                governance_declaration_path=DECLARATION,
                repository_root=ROOT,
                markdown_output_path=markdown,
            )
            first_text = markdown.read_text(encoding="utf-8")
            second = build_generated_publication_preview(
                spec_path=SPEC,
                ledger_path=LEDGER,
                artifact_dir=root,
                governance_declaration_path=DECLARATION,
                repository_root=ROOT,
                markdown_output_path=markdown,
            )
            second_text = markdown.read_text(encoding="utf-8")
        self.assertEqual(first["status"], "TECHNICAL_PUBLICATION_PREVIEW_GENERATED_NOT_AUTHORISED")
        self.assertEqual(first["claim_count"], 13)
        self.assertEqual(first["evidence_reference_count"], 42)
        self.assertEqual(first["markdown_sha256"], second["markdown_sha256"])
        self.assertEqual(first_text, second_text)
        self.assertIn("NOT AUTHORISED FOR PUBLICATION", first_text)
        self.assertEqual(first_text.count("### `CLAIM-"), 13)

    def test_preview_lists_actual_artifact_pointers_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            markdown = root / "preview.md"
            report = build_generated_publication_preview(
                spec_path=SPEC,
                ledger_path=LEDGER,
                artifact_dir=root,
                governance_declaration_path=DECLARATION,
                repository_root=ROOT,
                markdown_output_path=markdown,
            )
            text = markdown.read_text(encoding="utf-8")
        self.assertIn("model-relative-metric-analysis.json/metrics/0/numerator", text)
        self.assertIn("artifact hash `sha256:", text)
        self.assertIn("Governance status: `OWNER_GOVERNANCE_APPROVED_GENERATION_READY`", text)
        self.assertNotIn("Licence, copyright, author and contributor metadata require owner approval.", text)
        self.assertNotIn("OWNER_LICENSE_AND_CITATION_DECLARATION_PENDING", report["promotion_blockers"])

    def test_stale_claim_ledger_blocks_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            path = root / "candidate-priority-report.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["edge_count"] = 8
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(GeneratedPublicationError):
                build_generated_publication_preview(
                    spec_path=SPEC,
                    ledger_path=LEDGER,
                    artifact_dir=root,
                    governance_declaration_path=DECLARATION,
                    repository_root=ROOT,
                )

    def test_every_ledger_claim_must_be_placed_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            spec = json.loads(SPEC.read_text(encoding="utf-8"))
            spec["sections"][0]["claim_ids"].pop()
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(GeneratedPublicationError):
                build_generated_publication_preview(
                    spec_path=spec_path,
                    ledger_path=LEDGER,
                    artifact_dir=root,
                    governance_declaration_path=DECLARATION,
                    repository_root=ROOT,
                )

    def test_spec_cannot_authorise_publication_or_legal_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            spec = json.loads(SPEC.read_text(encoding="utf-8"))
            spec["status"] = "PUBLICATION_READY"
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(GeneratedPublicationError):
                build_generated_publication_preview(
                    spec_path=spec_path,
                    ledger_path=LEDGER,
                    artifact_dir=root,
                    governance_declaration_path=DECLARATION,
                    repository_root=ROOT,
                )


if __name__ == "__main__":
    unittest.main()
