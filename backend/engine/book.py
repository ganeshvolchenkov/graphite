"""Event-driven order book simulator. Resolution-agnostic: the script sets the step size,
so the same engine runs 60s equity bars or 50ms FX microstructure ticks."""

import math
import random

from contracts import ScenarioScript

LEVELS = 5
BASE_LEVEL_SIZE = 400.0
LEVEL_DECAY = 0.35
FULL_SIDE_DEPTH = sum(BASE_LEVEL_SIZE / (1 + i * LEVEL_DECAY) for i in range(LEVELS))


def _ramp(now_ms: int, at_ms: int, over_ms: int) -> float:
    """0.0 before the event, linear to 1.0 across over_ms, 1.0 after."""
    if now_ms < at_ms:
        return 0.0
    if over_ms <= 0:
        return 1.0
    return min(1.0, (now_ms - at_ms) / over_ms)


def _active(now_ms: int, at_ms: int, duration_ms: int) -> bool:
    return at_ms <= now_ms < at_ms + duration_ms


def _spread_target(script: ScenarioScript, now_ms: int, baseline: float) -> float:
    spread = baseline
    for event in script.events:
        if event.type != "spread_shock":
            continue
        target = event.to_spread_bps
        if target is None and event.to_spread_pips is not None:
            target = script.instrument.pips_to_bps(event.to_spread_pips)
        if target is None:
            continue
        progress = _ramp(now_ms, event.at_ms, event.over_ms)
        spread = spread + (target - spread) * progress
    return max(0.05, spread)


def _depth_multipliers(script: ScenarioScript, now_ms: int) -> tuple[float, float]:
    bid, ask = 1.0, 1.0
    for event in script.events:
        if event.type != "depth_evaporation":
            continue
        progress = _ramp(now_ms, event.at_ms, event.over_ms)
        remaining = 1.0 - (event.pct / 100.0) * progress
        if event.side in ("bid", "both"):
            bid *= remaining
        if event.side in ("ask", "both"):
            ask *= remaining
    return max(0.0, bid), max(0.0, ask)


def _drift_and_vol(script: ScenarioScript, now_ms: int, step_ms: int) -> tuple[float, float]:
    drift, vol_mult = 0.0, 1.0
    for event in script.events:
        if event.type == "price_impulse":
            move = event.move_pct
            if move is None and event.move_pips is not None:
                move = event.move_pips * script.instrument.pip_size / script.instrument.start_price * 100.0
            if move is None:
                continue
            span = max(step_ms, event.over_ms)
            if _active(now_ms, event.at_ms, span):
                drift += (move / 100.0) * (step_ms / span)
        elif event.type == "recovery":
            if _active(now_ms, event.at_ms, event.over_ms):
                reclaim = 0.0
                for other in script.events:
                    if other.type == "price_impulse" and other.move_pct:
                        reclaim -= other.move_pct * (event.reclaim_pct / 100.0)
                drift += (reclaim / 100.0) * (step_ms / max(step_ms, event.over_ms))
        elif event.type == "volatility_regime":
            progress = _ramp(now_ms, event.at_ms, event.over_ms)
            vol_mult = 1.0 + (event.multiplier - 1.0) * progress
    return drift, vol_mult


def _flags(script: ScenarioScript, now_ms: int) -> tuple[bool, bool, bool, float, str]:
    stale = halted = crossed = False
    toxic = 0.0
    toxic_dir = "sell"
    for event in script.events:
        if event.type == "feed_freeze" and _active(now_ms, event.at_ms, event.duration_ms):
            stale = True
        elif event.type == "halt" and _active(now_ms, event.at_ms, event.duration_ms):
            halted = True
        elif event.type == "crossed_book" and _active(now_ms, event.at_ms, event.duration_ms):
            crossed = True
        elif event.type == "toxic_flow" and _active(now_ms, event.at_ms, event.duration_ms):
            toxic = max(toxic, event.intensity)
            toxic_dir = event.direction
    return stale, halted, crossed, toxic, toxic_dir


def _phase(script: ScenarioScript, now_ms: int) -> str:
    shock_at = min((e.at_ms for e in script.events if e.type in ("price_impulse", "spread_shock", "gap")), default=None)
    recovery = next((e for e in script.events if e.type == "recovery"), None)
    if shock_at is None or now_ms < shock_at:
        return "warmup"
    if recovery and now_ms >= recovery.at_ms:
        return "recovery" if now_ms < recovery.at_ms + recovery.over_ms else "stabilised"
    return "shock"


def build_book_path(script: ScenarioScript, seed: int) -> list[dict]:
    """One row per step: mid, ladders, spread, and the regime flags a strategy can see."""
    rng = random.Random(seed)
    step_ms = script.resolution_ms
    baseline = script.baseline_bps()
    price = script.instrument.start_price
    for event in script.events:
        if event.type == "gap":
            price *= 1.0 + event.move_pct / 100.0
            break

    base_vol = 0.0006 * math.sqrt(step_ms / 60_000.0)
    rows: list[dict] = []
    last_visible: dict | None = None

    for index in range(script.steps):
        now_ms = index * step_ms
        drift, vol_mult = _drift_and_vol(script, now_ms, step_ms)
        stale, halted, crossed, toxic, toxic_dir = _flags(script, now_ms)

        if not halted:
            price *= 1.0 + drift + rng.gauss(0.0, base_vol * vol_mult)

        spread_bps = _spread_target(script, now_ms, baseline)
        bid_mult, ask_mult = _depth_multipliers(script, now_ms)
        half = price * (spread_bps / 2.0) / 10_000.0
        bid, ask = price - half, price + half
        if crossed:
            invert = next(
                (e.invert_bps for e in script.events
                 if e.type == "crossed_book" and _active(now_ms, e.at_ms, e.duration_ms)),
                5.0,
            )
            shift = price * (invert / 2.0) / 10_000.0
            bid, ask = price + shift, price - shift

        bids = [
            {"price": round(bid - i * half * 0.6, 6),
             "size": round(BASE_LEVEL_SIZE * bid_mult / (1 + i * LEVEL_DECAY), 2)}
            for i in range(LEVELS)
        ]
        asks = [
            {"price": round(ask + i * half * 0.6, 6),
             "size": round(BASE_LEVEL_SIZE * ask_mult / (1 + i * LEVEL_DECAY), 2)}
            for i in range(LEVELS)
        ]
        depth_bid = round(sum(level["size"] for level in bids), 2)
        depth_ask = round(sum(level["size"] for level in asks), 2)
        total = depth_bid + depth_ask

        row = {
            "index": index,
            "t_ms": now_ms,
            "clock": _clock(now_ms, step_ms),
            "phase": _phase(script, now_ms),
            "price": round(price, 6),
            "bid": round(bid, 6),
            "ask": round(ask, 6),
            "spread_bps": round(spread_bps, 3),
            "spread_pips": round(spread_bps / 10_000.0 * price / script.instrument.pip_size, 3),
            "bids": bids,
            "asks": asks,
            "depth_bid": depth_bid,
            "depth_ask": depth_ask,
            "imbalance": round((depth_bid - depth_ask) / total, 4) if total else 0.0,
            "liquidity_pct": round((depth_bid + depth_ask) / (2 * FULL_SIDE_DEPTH) * 100.0, 2),
            "volatility_pct": round(min(100.0, 8.0 * vol_mult), 2),
            "stale": stale,
            "halted": halted,
            "crossed": crossed,
            "toxic": round(toxic, 3),
            "toxic_direction": toxic_dir,
            "atr": round(price * base_vol * vol_mult * math.sqrt(14), 6),
        }

        if stale and last_visible is not None:
            for field in ("price", "bid", "ask", "bids", "asks", "spread_bps", "spread_pips", "depth_bid", "depth_ask"):
                row[field] = last_visible[field]
        else:
            last_visible = row

        rows.append(row)

    _attach_rolling(rows)
    return rows


def _clock(now_ms: int, step_ms: int) -> str:
    total_s = 9 * 3600 + 30 * 60 + now_ms // 1000
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    if step_ms < 1000:
        return f"{h:02d}:{m:02d}:{s:02d}.{now_ms % 1000:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def _attach_rolling(rows: list[dict], window: int = 12) -> None:
    for index, row in enumerate(rows):
        past = [r["price"] for r in rows[max(0, index - window) : index]]
        row["rolling_high"] = round(max(past), 6) if past else row["price"]
        row["rolling_low"] = round(min(past), 6) if past else row["price"]
