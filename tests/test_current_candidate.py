from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.current_candidate import (
    EXPECTED_ASEAN_FORMER_RULES,
    EXPECTED_POINT_A_IDS,
    REQUIRED_ART19_SLOTS,
    build_current_candidate_report,
    validate_current_candidate,
)


CANDIDATE = "policies/current_candidate_graph_2026-08-02.json"
VISUAL = "sources/reviews/vn_decision_33_2026.visual.json"


class CurrentCandidateTests(unittest.TestCase):
    def _payload(self) -> dict:
        return json.loads(Path(CANDIDATE).read_text(encoding="utf-8"))

    def _validate_mutation(self, payload: dict) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return validate_current_candidate(path, decision33_visual_path=VISUAL)

    def test_candidate_is_structurally_valid_but_quantitatively_blocked(self) -> None:
        self.assertEqual(validate_current_candidate(CANDIDATE), [])
        report = build_current_candidate_report(CANDIDATE)
        self.assertEqual(report["status"], "VALIDATED_PROVISIONAL_GRAPH")
        self.assertEqual(report["validation_errors"], [])
        self.assertGreater(report["binding_rule_count"], 0)
        self.assertEqual(report["removed_legacy_rule_count"], 3)
        self.assertEqual(report["non_binding_policy_object_count"], 4)
        self.assertEqual(report["evaluation_gate"]["typed_graph_validation"], "ALLOWED")
        self.assertEqual(report["evaluation_gate"]["quantitative_evaluation"], "BLOCKED")
        self.assertEqual(report["evaluation_gate"]["directional_gap_metrics"], "BLOCKED")
        self.assertEqual(report["evaluation_gate"]["actor_mismatch_metrics"], "BLOCKED")
        self.assertFalse(report["attestation"]["independent_review_completed"])
        self.assertFalse(report["attestation"]["current_quantitative_results_exist"])

    def test_point_a_route_matches_visual_review(self) -> None:
        payload = self._payload()
        point_a = next(
            rule
            for rule in payload["binding_rule_graph"]
            if rule["id"] == "VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE"
        )
        self.assertEqual(
            set(point_a["activation_model"]["catalog_item_ids"]),
            EXPECTED_POINT_A_IDS,
        )
        report = build_current_candidate_report(CANDIDATE)
        self.assertEqual(report["article13_route_gate"]["point_a_count"], 6)
        self.assertEqual(report["article13_route_gate"]["point_b_count"], 40)

    def test_article19_graph_contains_every_required_slot(self) -> None:
        payload = self._payload()
        slots = {
            consequence["normative_slot"]
            for rule in payload["binding_rule_graph"]
            if rule["id"].startswith("VN_ND142_ART19_")
            for consequence in rule["consequences"]
        }
        self.assertTrue(REQUIRED_ART19_SLOTS <= slots)

    def test_all_asean_legacy_rules_move_to_non_binding_layers(self) -> None:
        payload = self._payload()
        former_ids = {
            item["former_legacy_rule_id"]
            for item in payload["non_binding_policy_objects"]
        }
        self.assertEqual(former_ids, EXPECTED_ASEAN_FORMER_RULES)
        self.assertTrue(
            all(
                item["object_type"]
                in {"VOLUNTARY_GUIDING_PRINCIPLE", "POLICY_RECOMMENDATION_DIMENSION"}
                for item in payload["non_binding_policy_objects"]
            )
        )

    def test_enabling_quantitative_evaluation_is_rejected(self) -> None:
        payload = self._payload()
        payload["evaluation_policy"]["quantitative_evaluation_allowed"] = True
        errors = self._validate_mutation(payload)
        self.assertTrue(any("quantitative_evaluation_allowed" in error for error in errors))

    def test_reintroducing_unacceptable_shortcut_is_rejected(self) -> None:
        payload = self._payload()
        payload["binding_rule_graph"][0]["activation_model"]["required_facts"].append(
            "Unacceptable"
        )
        errors = self._validate_mutation(payload)
        self.assertTrue(any("Unacceptable-tier shortcut" in error for error in errors))

    def test_removing_article19_slot_is_rejected(self) -> None:
        payload = self._payload()
        rule = next(
            rule
            for rule in payload["binding_rule_graph"]
            if rule["id"] == "VN_ND142_ART19_4_PRELIMINARY_REPORTING"
        )
        rule["consequences"] = [
            consequence
            for consequence in rule["consequences"]
            if consequence["normative_slot"]
            != "serious_incident_preliminary_report_fallback"
        ]
        errors = self._validate_mutation(payload)
        self.assertTrue(any("Article 19 typed duty graph" in error for error in errors))

    def test_point_a_route_drift_is_rejected(self) -> None:
        payload = self._payload()
        point_a = next(
            rule
            for rule in payload["binding_rule_graph"]
            if rule["id"] == "VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE"
        )
        point_a["activation_model"]["catalog_item_ids"].pop()
        errors = self._validate_mutation(payload)
        self.assertTrue(any("point-a catalog IDs" in error for error in errors))

    def test_asean_object_cannot_be_promoted_to_binding_type(self) -> None:
        payload = self._payload()
        payload["non_binding_policy_objects"][0]["object_type"] = "BINDING_RULE"
        errors = self._validate_mutation(payload)
        self.assertTrue(any("non-binding policy layer" in error for error in errors))

    def test_duplicate_normative_slot_requires_explicit_resolution(self) -> None:
        payload = self._payload()
        first_slot = payload["binding_rule_graph"][0]["consequences"][0][
            "normative_slot"
        ]
        payload["binding_rule_graph"][1]["consequences"][0][
            "normative_slot"
        ] = first_slot
        errors = self._validate_mutation(payload)
        self.assertTrue(any("duplicate normative slots" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
