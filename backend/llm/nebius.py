import json
import os
import time

import openai
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

BASE_URL = "https://api.tokenfactory.nebius.com/v1/"

REASONING_MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"
CODE_MODEL = "deepseek-ai/DeepSeek-V4-Pro"


class NebiusError(Exception):
    """Raised when Nebius is unreachable, rate limited, or returns unusable output."""


def get_client() -> AsyncOpenAI:
    key = os.getenv("NEBIUS_API_KEY")
    if not key:
        raise NebiusError("NEBIUS_API_KEY is not set")
    return AsyncOpenAI(api_key=key, base_url=BASE_URL)


async def chat_json(
    system: str,
    user: str,
    model: str = REASONING_MODEL,
    temperature: float = 0.2,
) -> tuple[dict, dict]:
    return await chat_json_messages(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
        temperature=temperature,
    )


async def chat_json_messages(
    messages: list[dict],
    model: str = REASONING_MODEL,
    temperature: float = 0.2,
) -> tuple[dict, dict]:
    """Return (parsed_json, telemetry). Telemetry carries the benchmark numbers."""
    client = get_client()
    started = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
    except openai.RateLimitError as exc:
        raise NebiusError(f"{model} rate limit reached") from exc
    except openai.APIConnectionError as exc:
        raise NebiusError(f"could not reach Nebius for {model}") from exc
    except openai.APIStatusError as exc:
        raise NebiusError(f"{model} returned HTTP {exc.status_code}") from exc

    elapsed_ms = (time.perf_counter() - started) * 1000
    usage = response.usage
    telemetry = {
        "model": model,
        "latency_ms": round(elapsed_ms, 1),
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
    }

    content = (response.choices[0].message.content or "").strip()
    if content.startswith("```"):
        content = content.split("```")[1].removeprefix("json").strip()

    try:
        return json.loads(content), telemetry
    except json.JSONDecodeError as exc:
        raise NebiusError(f"{model} returned malformed JSON") from exc
