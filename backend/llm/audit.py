import json

from contracts import AuditReport, AuditRequest, Weakness

from .nebius import CODE_MODEL, chat_json

SYSTEM = """You are a senior quant risk reviewer auditing an algorithmic trading strategy
after a stress simulation. The strategy was actually executed against the simulated market,
so the metrics are measured, not estimated. You are given the source, those metrics, a
static analysis of which defensive controls exist, and any runtime exception it raised.

Ground every claim in the supplied metrics and the static analysis. Do not invent numbers.
If the strategy raised a runtime exception, that is the single most important finding:
report it as critical, name the exception, and explain which market condition triggered it.

Return JSON with exactly these keys:
  verdict: "passed" | "marginal" | "failed"
  score: integer 0-100 (risk-adjusted quality; below 40 means failed)
  headline: one sentence, under 90 characters
  narrative: 2-4 sentences explaining what happened and why
  strengths: array of 1-3 short strings
  weaknesses: array of objects {title, severity, detail}
  failureModes: array of objects {title, severity, detail}

severity must be one of: "low" | "medium" | "high" | "critical"."""

FALLBACK = AuditReport(
    verdict="failed",
    score=31,
    headline="Severe drawdown during liquidity shock: execution halts absent.",
    narrative=(
        "Offline fallback report. The strategy held exposure through the shock window "
        "without a stop or spread guard, so losses compounded as the book thinned."
    ),
    strengths=["Low turnover during the calm warmup regime"],
    weaknesses=[
        Weakness(
            title="Unconstrained order sizing into illiquid book",
            severity="critical",
            detail="Market orders continued while spread widened past 30 bps.",
        )
    ],
    failure_modes=[
        Weakness(
            title="Adverse selection on breakout triggers",
            severity="high",
            detail="Entries clustered immediately before the volatility cascade.",
        )
    ],
)


def _user_prompt(request: AuditRequest, guards: dict[str, bool]) -> str:
    metrics = request.metrics.model_dump(by_alias=True)
    worst = max(request.series, key=lambda t: t.drawdown_pct) if request.series else None
    crash = request.strategy_error
    crash_block = (
        f"RUNTIME EXCEPTION — the strategy crashed during execution:\n"
        f"  {crash.type}: {crash.message}\n"
        f"  raised at bar index {crash.index}; trading halted from that point.\n\n"
        if crash
        else "The strategy ran to completion without raising.\n\n"
    )
    return (
        f"Strategy name: {request.strategy_name}\n"
        f"Scenario: {request.scenario_name}\n\n"
        f"Source code:\n```python\n{request.code or '# source not supplied'}\n```\n\n"
        f"{crash_block}"
        f"Measured metrics:\n{json.dumps(metrics, indent=2)}\n\n"
        f"Static analysis of defensive controls (true = present):\n"
        f"{json.dumps(guards, indent=2)}\n\n"
        + (
            f"Worst tick: {worst.clock} price {worst.price} drawdown {worst.drawdown_pct}% "
            f"spread {worst.spread_bps} bps liquidity {worst.liquidity_pct}%\n"
            if worst
            else ""
        )
        + f"Market events:\n{json.dumps([e.model_dump(by_alias=True) for e in request.events], indent=2)}"
    )


async def audit(request: AuditRequest, guards: dict[str, bool], use_mock: bool = False) -> tuple[AuditReport, dict]:
    if use_mock:
        return FALLBACK, {"model": "mock"}

    payload, telemetry = await chat_json(
        SYSTEM, _user_prompt(request, guards), model=CODE_MODEL
    )
    report = AuditReport(
        verdict=payload.get("verdict", "failed"),
        score=int(payload.get("score", 0)),
        headline=payload.get("headline", "Audit complete."),
        narrative=payload.get("narrative", ""),
        strengths=payload.get("strengths", []),
        weaknesses=[Weakness.model_validate(w) for w in payload.get("weaknesses", [])],
        failure_modes=[Weakness.model_validate(f) for f in payload.get("failureModes", [])],
    )
    return report, telemetry
