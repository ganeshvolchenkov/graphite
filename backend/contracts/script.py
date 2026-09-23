from typing import Annotated, Literal, Union

from pydantic import Field

from .base import CamelModel

AssetClass = Literal["fx", "equity", "future", "crypto", "rates"]
QuoteUnit = Literal["pip", "bps", "pct"]
Side = Literal["bid", "ask", "both"]


class Instrument(CamelModel):
    symbol: str
    asset_class: AssetClass
    quote_unit: QuoteUnit
    start_price: float
    pip_size: float = 0.0001
    contract_size: float = 1.0

    def pips_to_bps(self, pips: float) -> float:
        return (pips * self.pip_size) / self.start_price * 10_000.0


class SpreadShock(CamelModel):
    type: Literal["spread_shock"] = "spread_shock"
    at_ms: int
    over_ms: int = 0
    to_spread_pips: float | None = None
    to_spread_bps: float | None = None


class DepthEvaporation(CamelModel):
    type: Literal["depth_evaporation"] = "depth_evaporation"
    at_ms: int
    over_ms: int = 0
    side: Side = "both"
    levels: int = 5
    pct: float = 90.0


class PriceImpulse(CamelModel):
    type: Literal["price_impulse"] = "price_impulse"
    at_ms: int
    over_ms: int = 0
    move_pct: float | None = None
    move_pips: float | None = None


class Gap(CamelModel):
    type: Literal["gap"] = "gap"
    at_ms: int
    move_pct: float


class FeedFreeze(CamelModel):
    type: Literal["feed_freeze"] = "feed_freeze"
    at_ms: int
    duration_ms: int


class CrossedBook(CamelModel):
    type: Literal["crossed_book"] = "crossed_book"
    at_ms: int
    duration_ms: int
    invert_bps: float = 5.0


class ToxicFlow(CamelModel):
    type: Literal["toxic_flow"] = "toxic_flow"
    at_ms: int
    duration_ms: int
    direction: Literal["buy", "sell"] = "sell"
    intensity: float = 0.8


class VolatilityRegime(CamelModel):
    type: Literal["volatility_regime"] = "volatility_regime"
    at_ms: int
    over_ms: int = 0
    multiplier: float = 3.0


class Halt(CamelModel):
    type: Literal["halt"] = "halt"
    at_ms: int
    duration_ms: int


class Recovery(CamelModel):
    type: Literal["recovery"] = "recovery"
    at_ms: int
    over_ms: int
    reclaim_pct: float = 35.0


ScenarioEvent = Annotated[
    Union[
        SpreadShock, DepthEvaporation, PriceImpulse, Gap, FeedFreeze,
        CrossedBook, ToxicFlow, VolatilityRegime, Halt, Recovery,
    ],
    Field(discriminator="type"),
]


class ScenarioScript(CamelModel):
    instrument: Instrument
    resolution_ms: int = Field(ge=10, le=300_000)
    duration_ms: int = Field(ge=1_000, le=14_400_000)
    baseline_spread_pips: float | None = None
    baseline_spread_bps: float | None = 1.8
    events: list[ScenarioEvent] = []

    @property
    def steps(self) -> int:
        return max(1, min(3_000, self.duration_ms // self.resolution_ms))

    def baseline_bps(self) -> float:
        if self.baseline_spread_bps is not None:
            return self.baseline_spread_bps
        if self.baseline_spread_pips is not None:
            return self.instrument.pips_to_bps(self.baseline_spread_pips)
        return 1.8
