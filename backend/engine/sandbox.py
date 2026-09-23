import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

WORKER = Path(__file__).parent / "worker.py"
TIMEOUT_SECONDS = 8


@dataclass
class ExecutionResult:
    ticks: list[dict]
    fills: list[dict]
    error: dict | None
    quotes: list[dict] = field(default_factory=list)
    stdout: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return bool(self.ticks) and self.error is None and not self.timed_out


def run_strategy(code: str, rows: list[dict]) -> ExecutionResult:
    """Execute the strategy in a separate process with a hard wall-clock limit.

    Isolation is demo-grade: separate process, stripped builtins, no __import__, timeout.
    It stops careless or crashing strategies from touching the API process. It is NOT a
    hardened boundary against a determined attacker — that needs container isolation.
    """
    payload = json.dumps({"code": code, "rows": rows})

    try:
        completed = subprocess.run(
            [sys.executable, str(WORKER)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=str(WORKER.parent),
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            ticks=[],
            fills=[],
            error={
                "type": "TimeoutError",
                "message": f"strategy exceeded {TIMEOUT_SECONDS}s wall clock (possible infinite loop)",
                "index": None,
            },
            timed_out=True,
        )

    if completed.returncode != 0:
        return ExecutionResult(
            ticks=[],
            fills=[],
            error={
                "type": "WorkerCrash",
                "message": (completed.stderr or "worker exited non-zero").strip()[:400],
                "index": None,
            },
        )

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return ExecutionResult(
            ticks=[],
            fills=[],
            error={"type": "WorkerOutput", "message": "worker returned unparseable output", "index": None},
        )

    return ExecutionResult(
        ticks=data["ticks"],
        fills=data["fills"],
        error=data["error"],
        quotes=data.get("quotes", []),
        stdout=data.get("stdout", ""),
    )
