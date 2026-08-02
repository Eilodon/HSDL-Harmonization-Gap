from __future__ import annotations

import unittest

from hsdl_gap.hsdl_core import (
    HEADER,
    HSDLCoreError,
    build_hsdl_differential_report,
    parse_policy_bundle,
    serialize_policy_bundle,
)
from hsdl_gap.loader import load_policy_bundle


class HSDLCoreTests(unittest.TestCase):
    def test_canonical_bundle_round_trips_exactly(self) -> None:
        policies = load_policy_bundle(
            "policies/legacy_v11.json",
            "alignments/legacy_duty_semantics.json",
        )
        document = serialize_policy_bundle(policies)
        self.assertTrue(document.startswith(HEADER + "\n"))
        self.assertEqual(parse_policy_bundle(document), policies)

    def test_full_space_differential_is_equivalent(self) -> None:
        report = build_hsdl_differential_report(
            "policies/legacy_v11.json",
            "alignments/legacy_duty_semantics.json",
        )
        self.assertEqual(report["status"], "EQUIVALENT")
        self.assertEqual(report["context_count"], 2880)
        self.assertEqual(report["comparison_count"], 51840)
        self.assertEqual(report["mismatch_count"], 0)
        self.assertEqual(report["mismatch_examples"], [])
        self.assertEqual(report["upstream_engine_compatibility"], "NOT_CLAIMED")

    def test_missing_header_is_rejected(self) -> None:
        with self.assertRaisesRegex(HSDLCoreError, "must begin"):
            parse_policy_bundle("policy {}\n")

    def test_unclosed_rule_is_rejected(self) -> None:
        document = "\n".join(
            [
                HEADER,
                'policy {"id":"P","jurisdiction":"T","version":"1"}',
                (
                    'rule {"bindingness":"BINDING","group":"G1",'
                    '"id":"R","instrument":"I","interpretation_status":'
                    '"reviewed","jurisdiction":"T","provision":"1",'
                    '"source_status":"final"}'
                ),
                'when {"op":"all"}',
                "endpolicy",
            ]
        )
        with self.assertRaises(HSDLCoreError):
            parse_policy_bundle(document)


if __name__ == "__main__":
    unittest.main()
