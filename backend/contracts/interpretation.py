from typing import Literal

from .base import CamelModel

RequirementStatus = Literal["modelled", "approximated", "unsupported"]

STATUS_WEIGHT = {"modelled": 1.0, "approximated": 0.5, "unsupported": 0.0}


class Requirement(CamelModel):
    """One demand the model found in the prompt, and what it did about it."""

    quote: str
    status: RequirementStatus
    mapped_to: str
    note: str


class Interpretation(CamelModel):
    summary: str
    instrument_reasoning: str
    resolution_reasoning: str
    confidence: float
    requirements: list[Requirement] = []

    @property
    def coverage_pct(self) -> float:
        if not self.requirements:
            return 0.0
        earned = sum(STATUS_WEIGHT[r.status] for r in self.requirements)
        return round(earned / len(self.requirements) * 100.0, 1)

    @property
    def counts(self) -> dict[str, int]:
        return {
            status: sum(1 for r in self.requirements if r.status == status)
            for status in ("modelled", "approximated", "unsupported")
        }
