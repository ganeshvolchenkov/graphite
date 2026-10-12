from typing import Literal

from .base import CamelModel
from .scenario import ScenarioRef

Phase = Literal["warmup", "shock", "recovery", "stabilised"]
Severity = Literal["info", "warn", "critical", "good"]
Variant = Literal["original", "improved"]


class Strategy(CamelModel):
    name: str
    code: str


class SimulationRequest(CamelModel):
    strategy: Strategy
    scenario: ScenarioRef
    variant: Variant = "original"


class Tick(CamelModel):
    index: int
    total: int
    phase: Phase
    clock: str
    price: float
    equity: float
    pnl: float
    drawdown_pct: float
    position: float
    trades: int
    spread_bps: float
    liquidity_pct: float
    volatility_pct: float


class MarketEvent(CamelModel):
    clock: str
    severity: Severity
    message: str


class Metrics(CamelModel):
    pnl: float
    pnl_pct: float
    max_drawdown_pct: float
    sharpe: float
    trades: int
    slippage_bps: float
    win_rate_pct: float
    exposure_minutes: int
    final_equity: float


class StrategyError(CamelModel):
    type: str
    message: str
    index: int | None = None


class AdapterInfo(CamelModel):
    adapted: bool = False
    interface: str = ""
    mapping: list[str] = []
    risks: list[str] = []
    notes: list[str] = []


class SimulationRun(CamelModel):
    id: str
    variant: Variant
    strategy_name: str
    scenario_name: str
    started_at: str
    series: list[Tick]
    events: list[MarketEvent]
    metrics: Metrics
    strategy_error: StrategyError | None = None
    adapter: AdapterInfo | None = None
