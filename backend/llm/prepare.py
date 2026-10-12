"""Turn whatever strategy source the user pasted into something the harness can run.

A runtime bug inside the user's logic is the product's output and must survive untouched.
Everything else — a different entry point, a missing adapter, an adapter that does not
compile — is our problem to solve silently.
"""

import ast
import logging

from contracts import CamelModel

from .adapt import adapt
from .nebius import CODE_MODEL, NebiusError, chat_json

logger = logging.getLogger(__name__)

ADAPTER_BANNER = "\n\n# ---- generated adapter ----\n"


class Preparation(CamelModel):
    code: str
    adapted: bool = False
    interface: str = ""
    mapping: list[str] = []
    risks: list[str] = []
    notes: list[str] = []


def has_on_tick(code: str) -> bool:
    """Module-level def on_tick taking at least three positional arguments."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "on_tick":
            args = node.args
            return len(args.args) + len(args.posonlyargs) >= 3
    return False


def syntax_error(code: str) -> str | None:
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return f"line {exc.lineno}: {exc.msg}"
    return None


SMOKE_ROWS = 12
SMOKE_TOLERANCE = 2


def smoke_failure(code: str, rows: list[dict]) -> str | None:
    """Run the first few calm rows. A failure there is the adapter's fault, not the
    strategy's — a real strategy bug needs market stress to surface, which has not
    happened yet this early in the run."""
    if not rows:
        return None
    from engine.sandbox import run_strategy

    result = run_strategy(code, rows[:SMOKE_ROWS])
    error = result.error
    if not error:
        return None
    index = error.get("index")
    if index is None or index <= SMOKE_TOLERANCE:
        where = "while loading" if index is None else f"on tick {index}"
        return f"{error['type']} {where}: {error['message']}"
    return None


async def _repair_adapter(code: str, adapter: str, problem: str) -> str:
    system = (
        "You are fixing a generated adapter that failed to compile. Return JSON with one "
        "key, \"adapter\", containing corrected Python that defines on_tick(bar, book, "
        "account) at module level. Do not modify or restate the user's strategy, and do "
        "not add guards the user did not write."
    )
    user = (
        f"Strategy source:\n```python\n{code}\n```\n\n"
        f"Broken adapter:\n```python\n{adapter}\n```\n\nProblem: {problem}"
    )
    payload, _ = await chat_json(system, user, model=CODE_MODEL, temperature=0.0)
    return payload.get("adapter", adapter)


async def prepare(
    code: str, use_mock: bool = False, smoke_rows: list[dict] | None = None
) -> Preparation:
    problem = syntax_error(code)
    if problem:
        return Preparation(code=code, notes=[f"Strategy has a syntax error ({problem})."])

    if has_on_tick(code):
        return Preparation(code=code, notes=["Strategy already implements on_tick."])

    if use_mock:
        return Preparation(code=code, notes=["Mock mode: adapter generation skipped."])

    try:
        adapter, telemetry = await adapt(code)
    except NebiusError as exc:
        logger.warning("adapter generation unavailable: %s", exc)
        return Preparation(code=code, notes=[f"Adapter generation unavailable: {exc}"])

    combined = code + ADAPTER_BANNER + adapter.adapter
    notes = [f"No on_tick found — generated an adapter with {telemetry.get('model', 'the code model')}."]

    problem = syntax_error(combined) or (None if has_on_tick(combined) else "adapter did not define on_tick")
    if problem:
        logger.info("repairing generated adapter: %s", problem)
        repaired = await _repair_adapter(code, adapter.adapter, problem)
        candidate = code + ADAPTER_BANNER + repaired
        if syntax_error(candidate) is None and has_on_tick(candidate):
            combined, adapter.adapter = candidate, repaired
            notes.append("First adapter failed to compile; repaired on the second attempt.")
        else:
            notes.append(f"Adapter could not be repaired ({problem}).")
            return Preparation(code=code, notes=notes)

    runtime_problem = smoke_failure(combined, smoke_rows or [])
    if runtime_problem:
        logger.info("adapter failed its smoke run, repairing: %s", runtime_problem)
        repaired = await _repair_adapter(code, adapter.adapter, runtime_problem)
        candidate = code + ADAPTER_BANNER + repaired
        if (
            syntax_error(candidate) is None
            and has_on_tick(candidate)
            and smoke_failure(candidate, smoke_rows or []) is None
        ):
            combined, adapter.adapter = candidate, repaired
            notes.append(f"Adapter broke on its first ticks ({runtime_problem}); repaired and re-verified.")
        else:
            notes.append(f"Adapter still failing after repair ({runtime_problem}).")

    return Preparation(
        code=combined,
        adapted=True,
        interface=adapter.interface,
        mapping=adapter.mapping,
        risks=adapter.risks,
        notes=notes,
    )
