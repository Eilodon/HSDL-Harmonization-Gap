from __future__ import annotations

import unittest

from hsdl_gap.migration_plan import build_migration_plan


AUDIT = "sources/reviews/legacy_v11_provision_audit.json"


class MigrationPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = build_migration_plan(AUDIT)

    def test_every_legacy_rule_has_one_migration_item(self) -> None:
        self.assertEqual(cls_plan := self.plan["legacy_rule_count"], 23)
        self.assertEqual(len(self.plan["rule_migrations"]), cls_plan)
        self.assertEqual(
            len({item["legacy_rule_id"] for item in self.plan["rule_migrations"]}),
            23,
        )

    def test_unsupported_rules_are_retracted(self) -> None:
        actions = {
            item["legacy_rule_id"]: item["migration_action"]
            for item in self.plan["rule_migrations"]
        }
        self.assertEqual(
            actions["VN_G2_ART13_REUSE"],
            "RETRACT_UNLESS_NEW_SOURCE_IDENTIFIED",
        )
        self.assertEqual(
            actions["VN_G6_ND142_EVENT"],
            "RETRACT_UNLESS_NEW_SOURCE_IDENTIFIED",
        )

    def test_duplicate_rule_is_not_carried_forward(self) -> None:
        item = next(
            item
            for item in self.plan["rule_migrations"]
            if item["legacy_rule_id"] == "EU_G6_ART9"
        )
        self.assertEqual(
            item["migration_action"],
            "REMOVE_DUPLICATE_AND_DERIVE_PROJECTION",
        )
        self.assertEqual(item["workstream"], "GROUP_ARCHITECTURE")

    def test_asean_rules_move_out_of_entity_rule_layer(self) -> None:
        actions = {
            item["legacy_rule_id"]: item["migration_action"]
            for item in self.plan["rule_migrations"]
            if item["legacy_rule_id"].startswith("ASEAN_")
        }
        self.assertEqual(len(actions), 4)
        self.assertTrue(
            set(actions.values())
            <= {"MOVE_TO_PRINCIPLE_LAYER", "MOVE_TO_RECOMMENDATION_LAYER"}
        )

    def test_workstreams_are_ordered_and_block_publication(self) -> None:
        sequences = [item["sequence"] for item in self.plan["workstreams"]]
        self.assertEqual(sequences, list(range(1, 7)))
        self.assertEqual(
            self.plan["promotion_gate"]["current_quantitative_results"],
            "BLOCKED",
        )
        self.assertEqual(
            self.plan["promotion_gate"]["manuscript_regeneration"],
            "BLOCKED",
        )
        self.assertTrue(
            self.plan["promotion_gate"]["implementation_may_begin_before_review"]
        )
        self.assertTrue(
            self.plan["promotion_gate"][
                "review_dependent_choices_must_remain_provisional"
            ]
        )

    def test_new_current_components_are_explicit(self) -> None:
        components = {
            item["id"]: item for item in self.plan["new_current_profile_components"]
        }
        self.assertIn("VN_DECISION33_CLASSIFICATION_RELATION", components)
        self.assertIn("VN_ARTICLE13_ROUTE_GRAPH", components)
        self.assertIn("VN_DECREE142_ARTICLE19_DUTY_GRAPH", components)
        self.assertIn("EU_CURRENT_HIGH_RISK_RELATION", components)
        self.assertIn("ASEAN_PRINCIPLE_AND_RECOMMENDATION_LAYERS", components)


if __name__ == "__main__":
    unittest.main()
