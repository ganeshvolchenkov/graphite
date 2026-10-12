from .audit import AuditReport
from .base import CamelModel


class ImproveRequest(CamelModel):
    code: str
    audit: AuditReport


class Recommendation(CamelModel):
    title: str
    problem: str
    change: str
    impact: str


class ImprovedStrategy(CamelModel):
    code: str
    summary: str
    recommendations: list[Recommendation]


class RunSummary(CamelModel):
    id: str
    strategy_name: str
    scenario_name: str
    verdict: str
    pnl: float
    at: str
