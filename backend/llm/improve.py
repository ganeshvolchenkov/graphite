import json

from contracts import ImprovedStrategy, ImproveRequest, Recommendation

from .nebius import CODE_MODEL, chat_json

SYSTEM = """You are a quant developer hardening an algorithmic trading strategy against the
failure modes found in an audit.

Rewrite the strategy so every critical and high-severity finding is addressed. Keep the
author's original structure and entry logic intact — add defensive controls, do not
redesign the alpha. The rewrite must be complete, runnable Python with no placeholders,
no TODOs, and no elided sections.

Return JSON with exactly these keys:
  code: the full patched Python source as a single string
  summary: one sentence listing the controls you added
  recommendations: array of objects {title, problem, change, impact}

Each recommendation must cite the specific measured number from the audit that motivated
it. Prefer explicit named thresholds over magic numbers."""

FALLBACK_CODE = '''MAX_SPREAD_BPS = 25.0
MIN_LIQUIDITY_PCT = 20.0
ATR_STOP_MULTIPLE = 2.0
MAX_POSITION = 120


def on_tick(bar, book, account):
    """Breakout entry with spread, liquidity, and trailing-stop guards."""
    if bar.spread_bps > MAX_SPREAD_BPS:
        return
    if book.liquidity_pct < MIN_LIQUIDITY_PCT:
        account.flatten()
        return

    stop_distance = ATR_STOP_MULTIPLE * bar.atr
    if account.position and bar.price <= account.entry_price - stop_distance:
        account.flatten()
        return

    if not account.position and bar.price > bar.rolling_high:
        size = min(MAX_POSITION, MAX_POSITION * book.liquidity_pct / 100.0)
        if size > 0:
            account.buy(size)
'''

FALLBACK = ImprovedStrategy(
    code=FALLBACK_CODE,
    summary="Added spread ceiling, liquidity floor, trailing ATR stop, and position cap.",
    recommendations=[
        Recommendation(
            title="Liquidity Guard",
            problem="Orders continued dispatching while the book thinned past 20%.",
            change="Flatten and stop trading when liquidity drops below MIN_LIQUIDITY_PCT.",
            impact="Removes fills during the widest-spread regime.",
        ),
        Recommendation(
            title="Trailing ATR Stop",
            problem="No stop allowed drawdown to compound through the shock window.",
            change="Exit when price falls ATR_STOP_MULTIPLE x ATR below entry.",
            impact="Caps single-trade loss instead of riding the impulse down.",
        ),
    ],
)


async def improve(request: ImproveRequest, use_mock: bool = False) -> tuple[ImprovedStrategy, dict]:
    if use_mock:
        return FALLBACK, {"model": "mock"}

    audit_json = json.dumps(request.audit.model_dump(by_alias=True), indent=2)
    user = (
        f"Original strategy:\n```python\n{request.code}\n```\n\n"
        f"Audit findings to remediate:\n{audit_json}"
    )
    payload, telemetry = await chat_json(SYSTEM, user, model=CODE_MODEL, temperature=0.1)

    improved = ImprovedStrategy(
        code=payload.get("code", request.code),
        summary=payload.get("summary", "Hardened strategy."),
        recommendations=[
            Recommendation.model_validate(r) for r in payload.get("recommendations", [])
        ],
    )
    return improved, telemetry
