"""Cross-model comprehension benchmark.

    python -m benchmarks.run [model ...]

Measures whether a model can read an institutional stress-scenario prompt and produce a
correct market event script: does it pick the right instrument, the right timescale, and
emit the events the prompt actually demands.
"""

import asyncio
import json
import sys
from pathlib import Path

from llm.scenario import interpret

from .cases import CASES
from .score import CaseResult, failed, score_case, summarise

DEFAULT_MODELS = [
    "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "deepseek-ai/DeepSeek-V4-Pro",
]

OUTPUT = Path(__file__).parent.parent / "benchmark_results.json"


async def run_model(model: str) -> list[CaseResult]:
    results: list[CaseResult] = []
    for case in CASES:
        try:
            scenario, telemetry = await interpret(case.prompt, model=model)
            result = score_case(case, scenario, telemetry)
        except Exception as exc:
            result = failed(case, model, f"{type(exc).__name__}: {exc}")
        results.append(result)
        flag = "ok " if result.ok else "ERR"
        print(f"  [{flag}] {case.name:26s} score={result.score:5.1f} "
              f"events={result.event_recall:.2f} params={result.param_accuracy:.2f} "
              f"instr={'Y' if result.instrument_ok else 'n'} "
              f"res={result.resolution_ms:>6}ms reqs={result.requirements_found} "
              f"{result.latency_ms:.0f}ms{' REPAIRED' if result.repaired else ''}"
              f"{' ' + result.error if result.error else ''}")
    return results


async def main() -> None:
    models = sys.argv[1:] or DEFAULT_MODELS
    payload = {"cases": [c.name for c in CASES], "models": [], "detail": []}

    for model in models:
        print(f"\n=== {model} ===")
        results = await run_model(model)
        summary = summarise(results)
        summary["model"] = model
        payload["models"].append(summary)
        payload["detail"].extend(r.as_dict() for r in results)

    print("\n" + "=" * 112)
    header = (f"{'MODEL':42s} {'SCORE':>6} {'EVENTS':>7} {'PARAMS':>7} {'INSTR':>6} {'RES':>6} "
              f"{'REQS':>5} {'REPAIR':>7} {'LATENCY':>9} {'TOKENS':>8}")
    print(header)
    print("-" * 112)
    for summary in sorted(payload["models"], key=lambda s: -s["score"]):
        print(f"{summary['model'][:42]:42s} {summary['score']:6.1f} "
              f"{summary['event_recall']:6.1f}% {summary['param_accuracy']:6.1f}% {summary['instrument_acc']:5.0f}% "
              f"{summary['resolution_acc']:5.0f}% {summary['avg_requirements']:5.1f} "
              f"{summary['repairs']:7d} {summary['avg_latency_ms']:8.0f}ms {summary['total_tokens']:8d}")

    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUTPUT.name}")


if __name__ == "__main__":
    asyncio.run(main())
