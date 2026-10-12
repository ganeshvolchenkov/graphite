"""Deterministic post-processing of a model-generated script.

The model is good at reading intent and bad at framing a window. These rules guarantee a
script that is actually stressful and actually plottable, and every adjustment is reported
back so the UI can show what was changed and why.
"""

from contracts import ScenarioScript
from contracts.script import PriceImpulse

MIN_STEPS = 220
MAX_STEPS = 2400
WARMUP_RATIO = 0.6
TAIL_RATIO = 1.5


def _event_end(event) -> int:
    span = getattr(event, "over_ms", 0) or getattr(event, "duration_ms", 0) or 0
    return event.at_ms + span


def _severity(script: ScenarioScript) -> float:
    """0-1: how badly the book is damaged, used to size an inferred price move."""
    depth = max(
        (e.pct for e in script.events if e.type == "depth_evaporation"), default=0.0
    )
    toxic = max((e.intensity for e in script.events if e.type == "toxic_flow"), default=0.0)
    baseline = script.baseline_bps()
    widened = baseline
    for event in script.events:
        if event.type != "spread_shock":
            continue
        target = event.to_spread_bps
        if target is None and event.to_spread_pips is not None:
            target = script.instrument.pips_to_bps(event.to_spread_pips)
        widened = max(widened, target or 0.0)
    blowout = min(1.0, (widened / baseline - 1.0) / 40.0) if baseline else 0.0
    return min(1.0, 0.45 * depth / 100.0 + 0.35 * toxic + 0.20 * blowout)


def normalize(script: ScenarioScript) -> tuple[ScenarioScript, list[str]]:
    notes: list[str] = []
    events = list(script.events)
    if not events:
        return script, notes

    # 1. A damaged book with no price move is not a stress test. Infer the move.
    if not any(e.type == "price_impulse" for e in events):
        severity = _severity(script)
        if severity > 0.15:
            toxic = next((e for e in events if e.type == "toxic_flow"), None)
            sign = -1.0 if (toxic is None or toxic.direction == "sell") else 1.0
            ceiling = 1.2 if script.instrument.asset_class == "fx" else 6.0
            move = round(sign * severity * ceiling, 3)
            anchor = min(e.at_ms for e in events)
            span = max(
                (_event_end(e) - anchor for e in events), default=script.resolution_ms
            )
            events.append(
                PriceImpulse(at_ms=anchor, over_ms=max(span, script.resolution_ms), move_pct=move)
            )
            notes.append(
                f"No price move was specified, but the book damage implies one — "
                f"inferred a {move:+.2f}% impulse over {max(span, script.resolution_ms)}ms."
            )

    # 2. Give the chart a calm baseline before the first event.
    earliest = min(e.at_ms for e in events)
    latest = max(_event_end(e) for e in events)
    core = max(latest - earliest, script.resolution_ms)
    warmup = max(int(core * WARMUP_RATIO), script.resolution_ms * 40)
    if earliest < warmup:
        shift = warmup - earliest
        events = [e.model_copy(update={"at_ms": e.at_ms + shift}) for e in events]
        notes.append(f"Shifted events {shift}ms later so the run opens with a calm baseline.")
        latest += shift

    # 3. Leave an aftermath, and keep the step count in a plottable range.
    duration = latest + max(int(core * TAIL_RATIO), script.resolution_ms * 60)
    duration = max(duration, MIN_STEPS * script.resolution_ms)
    duration = min(duration, MAX_STEPS * script.resolution_ms)
    if duration != script.duration_ms:
        notes.append(
            f"Set the window to {duration}ms "
            f"({duration // script.resolution_ms} steps at {script.resolution_ms}ms) "
            "to include the aftermath."
        )

    return script.model_copy(update={"events": events, "duration_ms": duration}), notes
