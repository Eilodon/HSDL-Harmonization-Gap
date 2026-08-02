from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.conditions_v2 import ConditionV2Error, evaluate_condition_v2
from hsdl_gap.context_v2 import (
    ContextV2,
    FixtureType,
    generate_single_fault_contexts,
    numeric_boundary_mutations,
)
from hsdl_gap.experiment import (
    MetricDefinition,
    UnknownPolicy,
    build_experiment_envelope,
    compute_corpus_share,
)
from hsdl_gap.schema_inventory import build_schema_inventory, inspect_schema
from hsdl_gap.stable_id import EntityKind, StableId, content_sha256
from hsdl_gap.tristate import TruthValue, tri_and, tri_not, tri_or


ROOT = Path(__file__).resolve().parents[1]


class TruthValueTests(unittest.TestCase):
    def test_not(self) -> None:
        self.assertEqual(tri_not(TruthValue.TRUE), TruthValue.FALSE)
        self.assertEqual(tri_not(TruthValue.FALSE), TruthValue.TRUE)
        self.assertEqual(tri_not(TruthValue.UNKNOWN), TruthValue.UNKNOWN)

    def test_and_uses_kleene_logic(self) -> None:
        self.assertEqual(tri_and([TruthValue.TRUE, TruthValue.TRUE]), TruthValue.TRUE)
        self.assertEqual(tri_and([TruthValue.TRUE, TruthValue.UNKNOWN]), TruthValue.UNKNOWN)
        self.assertEqual(tri_and([TruthValue.UNKNOWN, TruthValue.FALSE]), TruthValue.FALSE)

    def test_or_uses_kleene_logic(self) -> None:
        self.assertEqual(tri_or([TruthValue.FALSE, TruthValue.FALSE]), TruthValue.FALSE)
        self.assertEqual(tri_or([TruthValue.FALSE, TruthValue.UNKNOWN]), TruthValue.UNKNOWN)
        self.assertEqual(tri_or([TruthValue.UNKNOWN, TruthValue.TRUE]), TruthValue.TRUE)

    def test_implicit_bool_is_forbidden(self) -> None:
        with self.assertRaises(TypeError):
            bool(TruthValue.TRUE)


class ConditionsV2Tests(unittest.TestCase):
    def test_missing_fact_returns_unknown_and_trace(self) -> None:
        condition = {
            "op": "eq",
            "args": [{"field": "system.automation"}, {"literal": "HIGH"}],
        }
        trace = evaluate_condition_v2(condition, {"system": {}})
        self.assertEqual(trace.value, TruthValue.UNKNOWN)
        self.assertEqual(trace.missing_facts, ("system.automation",))

    def test_false_result_preserves_missing_trace(self) -> None:
        condition = {
            "op": "and",
            "args": [
                {"op": "eq", "args": [{"field": "a"}, {"literal": False}]},
                {"op": "eq", "args": [{"field": "missing"}, {"literal": 1}]},
            ],
        }
        trace = evaluate_condition_v2(condition, {"a": True})
        self.assertEqual(trace.value, TruthValue.FALSE)
        self.assertEqual(trace.missing_facts, ("missing",))

    def test_temporal_boundary(self) -> None:
        condition = {
            "op": "on_or_after",
            "args": [
                {"field": "time.evaluation_date"},
                {"literal": "2026-08-15"},
            ],
        }
        below = evaluate_condition_v2(
            condition, {"time": {"evaluation_date": "2026-08-14"}}
        )
        exact = evaluate_condition_v2(
            condition, {"time": {"evaluation_date": "2026-08-15"}}
        )
        self.assertEqual(below.value, TruthValue.FALSE)
        self.assertEqual(exact.value, TruthValue.TRUE)

    def test_collection_operations(self) -> None:
        context = {"features": ["biometric", "high_automation"]}
        contains_all = {
            "op": "contains_all",
            "args": [
                {"field": "features"},
                {"literal": ["biometric", "high_automation"]},
            ],
        }
        overlaps = {
            "op": "overlaps",
            "args": [{"field": "features"}, {"literal": ["medical", "biometric"]}],
        }
        self.assertEqual(
            evaluate_condition_v2(contains_all, context).value, TruthValue.TRUE
        )
        self.assertEqual(evaluate_condition_v2(overlaps, context).value, TruthValue.TRUE)

    def test_exists_missing_and_known_are_distinct(self) -> None:
        context = {"x": None}
        self.assertEqual(
            evaluate_condition_v2(
                {"op": "exists", "args": [{"field": "x"}]}, context
            ).value,
            TruthValue.TRUE,
        )
        self.assertEqual(
            evaluate_condition_v2(
                {"op": "known", "args": [{"field": "x"}]}, context
            ).value,
            TruthValue.FALSE,
        )
        self.assertEqual(
            evaluate_condition_v2(
                {"op": "missing", "args": [{"field": "y"}]}, context
            ).value,
            TruthValue.TRUE,
        )

    def test_between(self) -> None:
        condition = {
            "op": "between",
            "args": [
                {"field": "score"},
                {"literal": 10},
                {"literal": 20},
            ],
        }
        self.assertEqual(
            evaluate_condition_v2(condition, {"score": 10}).value, TruthValue.TRUE
        )
        self.assertEqual(
            evaluate_condition_v2(condition, {"score": 21}).value, TruthValue.FALSE
        )

    def test_malformed_arity_is_rejected(self) -> None:
        with self.assertRaises(ConditionV2Error):
            evaluate_condition_v2(
                {"op": "eq", "args": [{"literal": 1}]},
                {},
            )


class ContextV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = ContextV2(
            context_id="context:decision33:VN_D33_DEMO_01",
            profile_id="profile:engineering:candidate-2026-08-02",
            fixture_type=FixtureType.POSITIVE_WITNESS,
            facts={"classification": {"threshold": 100}, "system": {"active": True}},
            provenance={"status": "SOURCE_DERIVED"},
        )

    def test_boundary_generator_emits_four_traceable_cases(self) -> None:
        mutations = numeric_boundary_mutations(
            mutation_prefix="threshold",
            field_path="classification.threshold",
            threshold=100,
        )
        cases = generate_single_fault_contexts(self.base, mutations)
        self.assertEqual(len(cases), 4)
        self.assertEqual(
            [case.fixture_type for case in cases],
            [
                FixtureType.BOUNDARY_BELOW,
                FixtureType.BOUNDARY_EXACT,
                FixtureType.BOUNDARY_ABOVE,
                FixtureType.UNKNOWN_FACT,
            ],
        )
        self.assertEqual(cases[0].facts["classification"]["threshold"], 99)
        self.assertNotIn("threshold", cases[3].facts["classification"])
        self.assertTrue(all(case.parent_context_id == self.base.context_id for case in cases))

    def test_derived_fixture_requires_parent(self) -> None:
        with self.assertRaises(ValueError):
            ContextV2(
                context_id="context:test:negative",
                profile_id="profile:test:v1",
                fixture_type=FixtureType.SINGLE_FAULT_NEGATIVE,
                facts={},
                provenance={"status": "SYNTHETIC_FIXTURE"},
            )

    def test_content_hash_is_deterministic(self) -> None:
        self.assertEqual(self.base.content_hash, self.base.content_hash)
        self.assertTrue(self.base.content_hash.startswith("sha256:"))


class ExperimentTests(unittest.TestCase):
    def test_lower_upper_bound_preserves_unknown_uncertainty(self) -> None:
        definition = MetricDefinition(
            metric_id="metric:test:share",
            measure_id="UNWEIGHTED_CORPUS_SHARE",
            numerator_definition="true observations",
            denominator_definition="all observations",
            unknown_policy=UnknownPolicy.LOWER_UPPER_BOUND,
        )
        result = compute_corpus_share(
            definition,
            [TruthValue.TRUE, TruthValue.FALSE, TruthValue.UNKNOWN],
        )
        self.assertIsNone(result.value)
        self.assertAlmostEqual(result.lower_bound or 0, 1 / 3)
        self.assertAlmostEqual(result.upper_bound or 0, 2 / 3)

    def test_exclude_unknown_changes_denominator_explicitly(self) -> None:
        definition = MetricDefinition(
            metric_id="metric:test:share",
            measure_id="UNWEIGHTED_CORPUS_SHARE",
            numerator_definition="true observations",
            denominator_definition="known observations",
            unknown_policy=UnknownPolicy.EXCLUDE_AND_REPORT,
        )
        result = compute_corpus_share(
            definition,
            [TruthValue.TRUE, TruthValue.FALSE, TruthValue.UNKNOWN],
        )
        self.assertEqual(result.denominator, 2)
        self.assertEqual(result.unknown_count, 1)
        self.assertEqual(result.value, 0.5)

    def test_envelope_cannot_claim_legal_validation(self) -> None:
        definition = MetricDefinition(
            metric_id="metric:test:share",
            measure_id="UNWEIGHTED_CORPUS_SHARE",
            numerator_definition="true observations",
            denominator_definition="all observations",
        )
        result = compute_corpus_share(definition, [True, False])
        envelope = build_experiment_envelope(
            profile_id="profile:test:v1",
            profile_payload={"profile_id": "profile:test:v1"},
            corpus_id="corpus:test:v1",
            corpus_payload={"corpus_id": "corpus:test:v1"},
            assumptions=["ASSUME_X", "ASSUME_X"],
            metric_definition=definition,
            metric_result=result,
        )
        self.assertEqual(envelope["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(envelope["legal_validation"], "NOT_ASSERTED")
        self.assertEqual(envelope["assumptions"], ["ASSUME_X"])
        self.assertRegex(envelope["profile"]["profile_hash"], r"^sha256:[0-9a-f]{64}$")


class SchemaInventoryTests(unittest.TestCase):
    def test_all_schemas_are_draft_2020_12_and_have_unique_ids(self) -> None:
        inventory = build_schema_inventory(ROOT / "schemas")
        self.assertEqual(inventory["status"], "SCHEMA_INVENTORY_VALID")
        self.assertGreaterEqual(inventory["schema_count"], 4)
        ids = [item["$id"] for item in inventory["schemas"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_schema_is_self_describing(self) -> None:
        for path in sorted((ROOT / "schemas").glob("*.schema.json")):
            inspected = inspect_schema(path)
            self.assertTrue(inspected["$id"].startswith("https://"))


class StableIdTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        identifier = StableId(EntityKind.RULE, "EU", "ART9.RMS")
        self.assertEqual(StableId.parse(str(identifier)), identifier)

    def test_invalid_component_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            StableId(EntityKind.RULE, "EU", "contains spaces")

    def test_canonical_hash_ignores_mapping_order(self) -> None:
        self.assertEqual(content_sha256({"a": 1, "b": 2}), content_sha256({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
