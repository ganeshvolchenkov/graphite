import math
import random

from contracts import Phase, ScenarioParams

OPEN_MINUTE = 9 * 60 + 30
START_PRICE = 4500.0
ROLLING_WINDOW = 12


def clock_at(index: int) -> str:
    total = OPEN_MINUTE + index
    return f"{total // 60:02d}:{total % 60:02d}:00"


def phase_at(index: int, params: ScenarioParams) -> Phase:
    warmup_end = max(1, (params.duration_minutes - params.shock_duration_minutes - params.recovery_minutes))
    shock_end = warmup_end + params.shock_duration_minutes
    recovery_end = shock_end + params.recovery_minutes
    if index < warmup_end:
        return "warmup"
    if index < shock_end:
        return "shock"
    if index < recovery_end:
        return "recovery"
    return "stabilised"


def _shock_progress(index: int, params: ScenarioParams) -> float:
    """0.0 before the shock, ramps to 1.0 across it, holds after."""
    warmup_end = max(1, (params.duration_minutes - params.shock_duration_minutes - params.recovery_minutes))
    if index < warmup_end:
        return 0.0
    span = max(1, params.shock_duration_minutes)
    return min(1.0, (index - warmup_end + 1) / span)


def _recovery_progress(index: int, params: ScenarioParams) -> float:
    warmup_end = max(1, (params.duration_minutes - params.shock_duration_minutes - params.recovery_minutes))
    shock_end = warmup_end + params.shock_duration_minutes
    if index < shock_end:
        return 0.0
    span = max(1, params.recovery_minutes)
    return min(1.0, (index - shock_end + 1) / span)


def build_price_path(params: ScenarioParams, seed: int) -> list[dict]:
    """Deterministic minute bars: calm warmup, directional shock, partial mean reversion."""
    rng = random.Random(seed)
    bars: list[dict] = []
    price = START_PRICE

    for index in range(params.duration_minutes):
        phase = phase_at(index, params)
        shock = _shock_progress(index, params)
        recovery = _recovery_progress(index, params)

        base_vol = 0.0006
        stress = 1.0 + (params.volatility_multiplier - 1.0) * shock * (1.0 - 0.55 * recovery)
        noise = rng.gauss(0.0, base_vol * stress)

        drift = 0.0
        if phase == "shock":
            drift = (params.shock_magnitude_pct / 100.0) / max(1, params.shock_duration_minutes)
        elif phase in ("recovery", "stabilised"):
            reclaim = 0.35 * (params.shock_magnitude_pct / 100.0)
            drift = -reclaim / max(1, params.recovery_minutes) if recovery < 1.0 else 0.0

        if index == 0 and params.gap_pct:
            price *= 1.0 + params.gap_pct / 100.0

        price *= 1.0 + drift + noise

        liquidity = params.liquidity_factor + (1.0 - params.liquidity_factor) * (1.0 - shock + 0.6 * shock * recovery)
        liquidity = min(1.0, max(0.02, liquidity))
        spread = 1.8 + (params.spread_bps - 1.8) * shock * (1.0 - 0.6 * recovery)
        vol_pct = min(100.0, 8.0 * stress)

        bars.append(
            {
                "index": index,
                "phase": phase,
                "clock": clock_at(index),
                "price": round(price, 2),
                "spread_bps": round(max(0.5, spread), 2),
                "liquidity_pct": round(liquidity * 100.0, 1),
                "volatility_pct": round(vol_pct, 1),
                "atr": round(price * base_vol * stress * math.sqrt(14), 2),
            }
        )

    _attach_rolling(bars, ROLLING_WINDOW)
    return bars


def _attach_rolling(bars: list[dict], window: int) -> None:
    """Rolling high/low over the trailing window, excluding the current bar."""
    for index, bar in enumerate(bars):
        past = [b["price"] for b in bars[max(0, index - window) : index]]
        bar["rolling_high"] = round(max(past), 2) if past else bar["price"]
        bar["rolling_low"] = round(min(past), 2) if past else bar["price"]
