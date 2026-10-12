from dataclasses import asdict, dataclass

from contracts import Scenario

from .cases import Case

WEIGHTS = {
    "events": 0.25,
    "params": 0.40,
    "instrument": 0.10,
    "resolution": 0.15,
    "requirements": 0.10,
}


def _param_accuracy(case, script) -> tuple[float, list[str]]:
    """Did the model carry the prompt's actual numbers into the script?"""
    if not case.param_checks:
        return 1.0, []
    passed, misses = 0, []
    for event_type, field_name, expected, tolerance in case.param_checks:
        values = [
            getattr(event, field_name, None)
            for event in script.events
            if event.type == event_type and getattr(event, field_name, None) is not None
        ]
        if not values:
            misses.append(f"{event_type}.{field_name}=missing")
            continue

        if tolerance is None:
            ok = any(value == expected for value in values)
            shown = values[0]
        else:
            # A prompt like "three accelerating waves" is legitimately modelled as several
            # events, so accept either a single matching value or the aggregate.
            limit = abs(expected) * tolerance
            total = sum(values)
            ok = any(abs(value - expected) <= limit for value in values) or abs(total - expected) <= limit
            shown = values[0] if len(values) == 1 else f"{values}->{total}"

        if ok:
            passed += 1
        else:
            misses.append(f"{event_type}.{field_name}={shown}!={expected}")
    return passed / len(case.param_checks), misses


@dataclass
class CaseResult:
    case: str
    model: str
    ok: bool
    event_recall: float
    param_accuracy: float
    param_misses: list[str]
    instrument_ok: bool
    resolution_ok: bool
    requirement_ratio: float
    forbidden_hits: int
    score: float
    requirements_found: int
    resolution_ms: int
    asset_class: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    repaired: bool
    error: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def failed(case: Case, model: str, error: str) -> CaseResult:
    return CaseResult(
        case=case.name, model=model, ok=False, event_recall=0.0, param_accuracy=0.0,
        param_misses=[], instrument_ok=False,
        resolution_ok=False, requirement_ratio=0.0, forbidden_hits=0, score=0.0,
        requirements_found=0, resolution_ms=0, asset_class="", latency_ms=0.0,
        prompt_tokens=0, completion_tokens=0, repaired=False, error=error[:200],
    )


def score_case(case: Case, scenario: Scenario, telemetry: dict) -> CaseResult:
    script = scenario.script
    produced = {event.type for event in script.events}

    recall = len(case.required_events & produced) / len(case.required_events)
    param_accuracy, param_misses = _param_accuracy(case, script)
    forbidden_hits = len(case.forbidden_events & produced)
    instrument_ok = script.instrument.asset_class == case.asset_class
    resolution_ok = case.min_resolution_ms <= script.resolution_ms <= case.max_resolution_ms
    found = len(scenario.requirements)
    requirement_ratio = min(1.0, found / case.expected_requirements)

    raw = (
        WEIGHTS["events"] * recall
        + WEIGHTS["params"] * param_accuracy
        + WEIGHTS["instrument"] * instrument_ok
        + WEIGHTS["resolution"] * resolution_ok
        + WEIGHTS["requirements"] * requirement_ratio
    )
    penalty = 0.10 * forbidden_hits
    score = max(0.0, round((raw - penalty) * 100, 1))

    return CaseResult(
        case=case.name,
        model=telemetry.get("model", ""),
        ok=True,
        event_recall=round(recall, 3),
        param_accuracy=round(param_accuracy, 3),
        param_misses=param_misses,
        instrument_ok=instrument_ok,
        resolution_ok=resolution_ok,
        requirement_ratio=round(requirement_ratio, 3),
        forbidden_hits=forbidden_hits,
        score=score,
        requirements_found=found,
        resolution_ms=script.resolution_ms,
        asset_class=script.instrument.asset_class,
        latency_ms=telemetry.get("latency_ms", 0.0),
        prompt_tokens=telemetry.get("prompt_tokens", 0),
        completion_tokens=telemetry.get("completion_tokens", 0),
        repaired=bool(telemetry.get("repaired")),
    )


def summarise(results: list[CaseResult]) -> dict:
    scored = [r for r in results if r.ok]
    n = len(scored) or 1
    return {
        "model": results[0].model if results else "",
        "cases": len(results),
        "succeeded": len(scored),
        "score": round(sum(r.score for r in scored) / n, 1),
        "event_recall": round(sum(r.event_recall for r in scored) / n * 100, 1),
        "param_accuracy": round(sum(r.param_accuracy for r in scored) / n * 100, 1),
        "instrument_acc": round(sum(r.instrument_ok for r in scored) / n * 100, 1),
        "resolution_acc": round(sum(r.resolution_ok for r in scored) / n * 100, 1),
        "avg_requirements": round(sum(r.requirements_found for r in scored) / n, 1),
        "repairs": sum(r.repaired for r in scored),
        "avg_latency_ms": round(sum(r.latency_ms for r in scored) / n),
        "total_tokens": sum(r.prompt_tokens + r.completion_tokens for r in results),
    }
