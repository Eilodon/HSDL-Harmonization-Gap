from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.context import Context
from hsdl_gap.evaluator import evaluate_policy
from hsdl_gap.loader import load_policy_bundle
from hsdl_gap.model import EvaluationState

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / "policies" / "legacy_v11.json"


class SemanticStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policies = load_policy_bundle(POLICIES)

    def test_ctxstar_has_no_priority_conflict(self) -> None:
        ctx = Context(
            risk_tier="High",
            sector="Healthcare",
            system_role="Provider",
            lifecycle_stage="PostMarket",
            modification_increases_risk=False,
            serious_harm_discovered=False,
            interacts_with_human=False,
            existing_sector_certification=False,
        )
        result = evaluate_policy(self.policies["VN"], ctx, "G1")
        self.assertEqual(result.active_rule_ids, ("VN_G1_ART10_5A",))
        self.assertEqual(result.flattened_obligors, frozenset({"Regulator"}))
        self.assertEqual(result.state, EvaluationState.DETERMINATE)

    def test_no_rule_is_distinct_from_unspecified_obligor(self) -> None:
        ctx = Context(
            risk_tier="Minimal",
            sector="Healthcare",
            system_role="User",
            lifecycle_stage="PostMarket",
            modification_increases_risk=False,
            serious_harm_discovered=False,
            interacts_with_human=False,
            existing_sector_certification=False,
        )
        eu = evaluate_policy(self.policies["EU"], ctx, "G3")
        vn = evaluate_policy(self.policies["VN"], ctx, "G3")
        self.assertEqual(eu.state, EvaluationState.NO_APPLICABLE_RULE)
        self.assertEqual(vn.state, EvaluationState.UNSPECIFIED_OBLIGOR)
        self.assertNotEqual(eu.state, vn.state)

    def test_g4_preserves_primary_fallback_relations(self) -> None:
        ctx = Context(
            risk_tier="High",
            sector="Healthcare",
            system_role="Provider",
            lifecycle_stage="PostMarket",
            modification_increases_risk=False,
            serious_harm_discovered=True,
            interacts_with_human=False,
            existing_sector_certification=False,
        )
        result = evaluate_policy(self.policies["VN"], ctx, "G4")
        relations = {duty.actor_relation.value for duty in result.duties}
        self.assertEqual(relations, {"primary", "fallback"})
        self.assertEqual(result.flattened_obligors, frozenset({"Provider", "Deployer"}))


if __name__ == "__main__":
    unittest.main()
