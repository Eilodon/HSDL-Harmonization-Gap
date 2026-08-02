from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import product
from typing import Iterator

RISK_TIERS = ("Minimal", "Limited", "Medium", "High", "Unacceptable")
SECTORS = ("Healthcare", "Finance", "Education", "PublicSafety", "GenAI", "Other")
SYSTEM_ROLES = ("Provider", "Deployer", "User")
LIFECYCLE_STAGES = ("PreMarket", "PostMarket")
BOOLS = (True, False)


@dataclass(frozen=True, slots=True)
class Context:
    risk_tier: str
    sector: str
    system_role: str
    lifecycle_stage: str
    modification_increases_risk: bool
    serious_harm_discovered: bool
    interacts_with_human: bool
    existing_sector_certification: bool

    def as_mapping(self) -> dict[str, object]:
        return asdict(self)


def iter_legacy_contexts() -> Iterator[Context]:
    """Yield the frozen v11 Cartesian context space in stable order."""
    for values in product(
        RISK_TIERS,
        SECTORS,
        SYSTEM_ROLES,
        LIFECYCLE_STAGES,
        BOOLS,
        BOOLS,
        BOOLS,
        BOOLS,
    ):
        yield Context(*values)
