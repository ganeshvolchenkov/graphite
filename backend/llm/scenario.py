import logging

from pydantic import ValidationError

from contracts import Interpretation, Scenario, ScenarioParams, ScenarioScript

from .nebius import REASONING_MODEL, chat_json_messages
from .normalize import normalize
from .params import derive_params
from .vocabulary import FEWSHOT_ANSWER, FEWSHOT_PROMPT, VOCABULARY

logger = logging.getLogger(__name__)

FALLBACK_PARAMS = ScenarioParams(
    shock_magnitude_pct=-8.0,
    volatility_multiplier=6.0,
    liquidity_factor=0.18,
    spread_bps=45.0,
    gap_pct=0.0,
    duration_minutes=90,
    shock_duration_minutes=5,
    recovery_minutes=40,
)

FALLBACK = Scenario(
    id="custom",
    name="Custom Scenario",
    prompt="",
    interpretation="Offline fallback: severe directional sell-off with a thin order book.",
    confidence=0.5,
    derived_from=["directional sell-off", "thin order book"],
    params=FALLBACK_PARAMS,
)


def _messages(prompt: str, repair: str | None = None) -> list[dict]:
    messages = [
        {"role": "system", "content": VOCABULARY},
        {"role": "user", "content": FEWSHOT_PROMPT},
        {"role": "assistant", "content": FEWSHOT_ANSWER},
        {"role": "user", "content": prompt},
    ]
    if repair:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Your previous answer failed schema validation with these errors:\n"
                    f"{repair}\n\nReturn the corrected JSON only."
                ),
            }
        )
    return messages


def _parse(payload: dict) -> tuple[ScenarioScript, Interpretation]:
    script = ScenarioScript.model_validate(payload["script"])
    reasoning = Interpretation.model_validate(payload["reasoning"])
    return script, reasoning


async def interpret(
    prompt: str, use_mock: bool = False, model: str = REASONING_MODEL
) -> tuple[Scenario, dict]:
    if use_mock:
        return FALLBACK.model_copy(update={"prompt": prompt}), {"model": "mock"}

    payload, telemetry = await chat_json_messages(_messages(prompt), model=model)
    try:
        script, reasoning = _parse(payload)
    except (ValidationError, KeyError) as first_error:
        logger.info("script failed validation, attempting one repair: %s", first_error)
        payload, telemetry = await chat_json_messages(
            _messages(prompt, repair=str(first_error)[:1500]), model=model
        )
        script, reasoning = _parse(payload)
        telemetry["repaired"] = True

    script, adjustments = normalize(script)
    telemetry["adjustments"] = adjustments

    scenario = Scenario(
        id="custom",
        name=f"{script.instrument.symbol} — custom scenario",
        prompt=prompt,
        interpretation=reasoning.summary,
        confidence=reasoning.confidence,
        derived_from=[r.quote for r in reasoning.requirements],
        params=derive_params(script),
        script=script,
        reasoning=reasoning,
        requirements=reasoning.requirements,
        coverage_pct=reasoning.coverage_pct,
        adjustments=adjustments,
        model=telemetry.get("model", ""),
    )
    return scenario, telemetry
