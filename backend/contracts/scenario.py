from .base import CamelModel
from .interpretation import Interpretation, Requirement
from .script import ScenarioScript


class ScenarioParams(CamelModel):
    shock_magnitude_pct: float
    volatility_multiplier: float
    liquidity_factor: float
    spread_bps: float
    gap_pct: float
    duration_minutes: int
    shock_duration_minutes: int
    recovery_minutes: int


class InterpretRequest(CamelModel):
    prompt: str


class ScenarioRef(CamelModel):
    id: str
    name: str
    params: ScenarioParams | None = None
    script: ScenarioScript | None = None


class Scenario(CamelModel):
    """The original contract, plus the richer script/coverage fields.

    `params` and `interpretation` stay so the existing frontend keeps working;
    `script`, `requirements` and `coveragePct` carry the expressive version.
    """

    id: str
    name: str
    prompt: str
    interpretation: str
    confidence: float
    derived_from: list[str]
    params: ScenarioParams
    script: ScenarioScript | None = None
    reasoning: Interpretation | None = None
    requirements: list[Requirement] = []
    coverage_pct: float = 0.0
    adjustments: list[str] = []
    model: str = ""
