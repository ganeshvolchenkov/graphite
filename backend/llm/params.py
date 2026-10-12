"""Collapse a rich event script down to the legacy 8-field params block.

The original frontend contract expects `params`; this keeps it accurate enough to drive
the old code path while the script carries the full fidelity.
"""

from contracts import ScenarioParams, ScenarioScript


def derive_params(script: ScenarioScript) -> ScenarioParams:
    impulse_pct = 0.0
    shock_ms = 0
    recovery_ms = 0
    gap_pct = 0.0
    vol_multiplier = 1.0
    depth_removed = 0.0
    target_spread = script.baseline_bps()

    for event in script.events:
        if event.type == "price_impulse":
            move = event.move_pct
            if move is None and event.move_pips is not None:
                move = event.move_pips * script.instrument.pip_size / script.instrument.start_price * 100.0
            impulse_pct += move or 0.0
            shock_ms = max(shock_ms, event.over_ms or script.resolution_ms)
        elif event.type == "gap":
            gap_pct += event.move_pct
        elif event.type == "volatility_regime":
            vol_multiplier = max(vol_multiplier, event.multiplier)
        elif event.type == "depth_evaporation":
            depth_removed = max(depth_removed, event.pct)
        elif event.type == "spread_shock":
            candidate = event.to_spread_bps
            if candidate is None and event.to_spread_pips is not None:
                candidate = script.instrument.pips_to_bps(event.to_spread_pips)
            target_spread = max(target_spread, candidate or 0.0)
        elif event.type == "recovery":
            recovery_ms = max(recovery_ms, event.over_ms)

    minutes = max(1, script.duration_ms // 60_000)
    return ScenarioParams(
        shock_magnitude_pct=round(impulse_pct, 3),
        volatility_multiplier=round(vol_multiplier, 3),
        liquidity_factor=round(max(0.01, 1.0 - depth_removed / 100.0), 4),
        spread_bps=round(target_spread, 3),
        gap_pct=round(gap_pct, 3),
        duration_minutes=minutes,
        shock_duration_minutes=max(1, shock_ms // 60_000) if shock_ms >= 60_000 else 1,
        recovery_minutes=max(0, recovery_ms // 60_000),
    )
