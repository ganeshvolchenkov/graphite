from contracts import (
    Instrument,
    MarketEvent,
    Metrics,
    ScenarioParams,
    ScenarioScript,
    Tick,
)

from .book import build_book_path
from .events import regime_events, strategy_events
from .metrics import build_metrics
from .sandbox import ExecutionResult, run_strategy
from .strategy import GuardProfile, detect_guards

START_EQUITY = 1_000_000.0


def script_from_params(params: ScenarioParams) -> ScenarioScript:
    """Legacy path: turn the old 8-field block into an equivalent minute-resolution script."""
    warmup_ms = max(
        60_000,
        (params.duration_minutes - params.shock_duration_minutes - params.recovery_minutes) * 60_000,
    )
    shock_ms = max(60_000, params.shock_duration_minutes * 60_000)
    events: list[dict] = [
        {"type": "price_impulse", "atMs": warmup_ms, "overMs": shock_ms,
         "movePct": params.shock_magnitude_pct},
        {"type": "volatility_regime", "atMs": warmup_ms, "overMs": shock_ms,
         "multiplier": params.volatility_multiplier},
        {"type": "depth_evaporation", "atMs": warmup_ms, "overMs": shock_ms, "side": "both",
         "levels": 5, "pct": (1.0 - params.liquidity_factor) * 100.0},
        {"type": "spread_shock", "atMs": warmup_ms, "overMs": shock_ms,
         "toSpreadBps": params.spread_bps},
    ]
    if params.gap_pct:
        events.append({"type": "gap", "atMs": 0, "movePct": params.gap_pct})
    if params.recovery_minutes:
        events.append({"type": "recovery", "atMs": warmup_ms + shock_ms,
                       "overMs": params.recovery_minutes * 60_000, "reclaimPct": 35.0})

    return ScenarioScript.model_validate(
        {
            "instrument": Instrument(
                symbol="ESZ6", asset_class="future", quote_unit="bps",
                start_price=4500.0, pip_size=1.0,
            ).model_dump(by_alias=True),
            "resolutionMs": 60_000,
            "durationMs": max(params.duration_minutes, 30) * 60_000,
            "baselineSpreadBps": 1.8,
            "events": events,
        }
    )


def _build_ticks(rows: list[dict], execution: ExecutionResult) -> tuple[list[Tick], float, list[float], int]:
    by_index = {row["index"]: row for row in execution.ticks}
    ticks: list[Tick] = []
    peak = START_EQUITY
    max_drawdown = 0.0
    returns: list[float] = []
    exposure = 0
    previous = START_EQUITY
    last = {"equity": START_EQUITY, "position": 0.0, "trades": 0}

    for row in rows:
        state = by_index.get(row["index"], last)
        last = state
        equity = state["equity"]

        if state["position"]:
            exposure += 1
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak * 100.0 if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        if previous:
            returns.append((equity - previous) / previous)
        previous = equity

        ticks.append(
            Tick(
                index=row["index"],
                total=len(rows),
                phase=row["phase"],
                clock=row["clock"],
                price=row["price"],
                equity=round(equity, 2),
                pnl=round(equity - START_EQUITY, 2),
                drawdown_pct=round(drawdown, 2),
                position=state["position"],
                trades=state["trades"],
                spread_bps=row["spread_bps"],
                liquidity_pct=row["liquidity_pct"],
                volatility_pct=row["volatility_pct"],
            )
        )

    return ticks, max_drawdown, returns, exposure


def _slippage_bps(fills: list[dict], rows: list[dict]) -> list[float]:
    costs = []
    for fill in fills:
        row = rows[fill["index"]]
        costs.append(abs(fill["price"] - row["price"]) / row["price"] * 10_000.0)
    return costs


def _win_count(fills: list[dict]) -> int:
    wins, opened = 0, None
    for fill in fills:
        if fill["side"] == "buy":
            opened = fill["price"]
        elif opened is not None:
            wins += 1 if fill["price"] > opened else 0
            opened = None
    return wins


def simulate_script(
    code: str, script: ScenarioScript, seed: int
) -> tuple[list[Tick], list[MarketEvent], Metrics, GuardProfile, ExecutionResult, list[dict]]:
    guards = detect_guards(code)
    rows = build_book_path(script, seed)
    execution = run_strategy(code, rows)

    ticks, max_drawdown, returns, exposure = _build_ticks(rows, execution)

    events = regime_events(rows, script)
    events.update(strategy_events(execution, rows))
    ordered = [events[key] for key in sorted(events)]

    metrics = build_metrics(
        equity=ticks[-1].equity if ticks else START_EQUITY,
        start_equity=START_EQUITY,
        max_drawdown=max_drawdown,
        returns=returns,
        slippage_costs=_slippage_bps(execution.fills, rows),
        trades=ticks[-1].trades if ticks else 0,
        wins=_win_count(execution.fills),
        exposure=exposure,
    )
    return ticks, ordered, metrics, guards, execution, rows


def simulate(
    code: str, params: ScenarioParams, seed: int
) -> tuple[list[Tick], list[MarketEvent], Metrics, GuardProfile, ExecutionResult]:
    ticks, events, metrics, guards, execution, _ = simulate_script(
        code, script_from_params(params), seed
    )
    return ticks, events, metrics, guards, execution
