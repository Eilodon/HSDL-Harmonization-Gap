from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.asean import build_asean_ontology_audit, load_asean_ontology, validate_asean_ontology

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "asean" / "guide_ontology_2024_2025.json"


class AseanOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ontology = load_asean_ontology(ONTOLOGY)
        cls.audit = build_asean_ontology_audit(ONTOLOGY)

    def test_official_object_counts_are_separate(self) -> None:
        self.assertEqual(len(self.ontology.guiding_principles), 7)
        self.assertEqual(len(self.ontology.governance_framework_areas), 4)
        self.assertEqual(len(self.ontology.genai_risks), 6)
        self.assertEqual(len(self.ontology.genai_policy_dimensions), 9)
        self.assertEqual(validate_asean_ontology(self.ontology), [])

    def test_genai_risks_are_multi_label(self) -> None:
        flags = self.ontology.validate_risk_flags(
            {"inaccurate_responses_disinformation", "privacy_confidentiality"}
        )
        self.assertEqual(len(flags), 2)
        self.assertFalse(self.ontology.risks_mutually_exclusive)
        self.assertEqual(self.ontology.risk_codomain, "power_set")

    def test_unknown_risk_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.ontology.validate_risk_flags({"societal"})

    def test_legacy_partition_claim_is_gated(self) -> None:
        self.assertEqual(
            self.audit["legacy_taxonomy"]["status"],
            "NOT_SUPPORTED_AS_THE_SIX_GENAI_RISKS_BY_THE_OFFICIAL_GUIDES",
        )
        self.assertEqual(
            self.audit["legacy_taxonomy"]["h7_2_gate"],
            "RETRACT_OR_REFORMULATE_AS_TYPED_MULTI_LABEL_COMPARISON",
        )


if __name__ == "__main__":
    unittest.main()
