from typing import Literal

from .base import CamelModel
from .scenario import ScenarioRef
from .simulation import MarketEvent, Metrics, StrategyError, Tick

Verdict = Literal["passed", "marginal", "failed"]
WeaknessSeverity = Literal["low", "medium", "high", "critical"]


class Weakness(CamelModel):
    title: str
    severity: WeaknessSeverity
    detail: str


class AuditRequest(CamelModel):
    id: str
    variant: str = "original"
    strategy_name: str
    scenario_name: str
    metrics: Metrics
    series: list[Tick] = []
    events: list[MarketEvent] = []
    code: str | None = None
    scenario: ScenarioRef | None = None
    strategy_error: StrategyError | None = None


class AuditReport(CamelModel):
    verdict: Verdict
    score: int
    headline: str
    narrative: str
    strengths: list[str]
    weaknesses: list[Weakness]
    failure_modes: list[Weakness]
