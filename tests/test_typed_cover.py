from __future__ import annotations

import unittest

from hsdl_gap.typed_cover import (
    CoverBlock,
    build_typed_cover_audit,
    quotient_cover,
    refinement_result,
)


class TypedCoverTests(unittest.TestCase):
    def _block(
        self,
        block_id: str,
        *,
        group: str = "G1",
        label: str = "slot",
        support: frozenset[int] = frozenset({1, 2}),
    ) -> CoverBlock:
        return CoverBlock(
            id=block_id,
            jurisdiction="T",
            group=group,
            label_mode="exact",
            label=label,
            support=support,
            member_ids=(block_id,),
        )

    def test_same_label_support_inclusion_refines(self) -> None:
        result = refinement_result(
            [self._block("A", support=frozenset({1}))],
            [self._block("B", support=frozenset({1, 2}))],
        )
        self.assertTrue(result["is_refinement"])
        self.assertEqual(result["uncovered"], [])

    def test_equal_support_with_different_label_does_not_refine(self) -> None:
        result = refinement_result(
            [self._block("A", label="classification")],
            [self._block("B", label="inspection")],
        )
        self.assertFalse(result["is_refinement"])
        self.assertEqual(result["uncovered_source_block_count"], 1)

    def test_equal_label_across_different_groups_does_not_refine(self) -> None:
        result = refinement_result(
            [self._block("A", group="G1")],
            [self._block("B", group="G4")],
        )
        self.assertFalse(result["is_refinement"])

    def test_quotient_collapses_only_equal_group_label_and_support(self) -> None:
        blocks = [
            self._block("A"),
            self._block("B"),
            self._block("C", label="other"),
            self._block("D", support=frozenset({1})),
        ]
        quotient = quotient_cover(blocks)
        self.assertEqual(len(quotient), 3)
        collapsed = next(block for block in quotient if set(block.member_ids) == {"A", "B"})
        self.assertEqual(collapsed.support, frozenset({1, 2}))

    def test_repository_audit_is_labeled_and_finite(self) -> None:
        report = build_typed_cover_audit(
            "policies/legacy_v11.json",
            "alignments/legacy_duty_semantics.json",
        )
        self.assertEqual(report["status"], "FINITE_TYPED_COVER_ORACLE_COMPLETE")
        self.assertEqual(report["context_count"], 2880)
        self.assertEqual(
            report["theorem_gate"]["legacy_H8"],
            "WITHDRAW_AND_REPLACE_WITH_LABELED_TYPED_COVER",
        )
        self.assertEqual(
            report["theorem_gate"]["legacy_Theorem_C_implementation_claim"],
            "NOT_IMPLEMENTED_BY_THIS_FINITE_ORACLE",
        )
        for label_mode in ("exact", "broad"):
            for cover_mode in ("indexed", "quotient"):
                self.assertEqual(
                    len(report["matrices"][label_mode][cover_mode]),
                    6,
                )


if __name__ == "__main__":
    unittest.main()
