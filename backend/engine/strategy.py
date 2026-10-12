import re
from dataclasses import dataclass

GUARD_PATTERNS = {
    "stop_loss": r"stop[_\s]?loss|trailing[_\s]?stop|atr[_\s]?stop|max[_\s]?loss",
    "spread_guard": r"spread[_\s]?bps|spread\s*[<>]|max[_\s]?spread",
    "liquidity_guard": r"liquidity|order[_\s]?book|depth|volume\s*[<>]",
    "position_limit": r"max[_\s]?position|position[_\s]?limit|max[_\s]?lot|max[_\s]?size",
    "circuit_breaker": r"circuit[_\s]?break|kill[_\s]?switch|halt|panic[_\s]?exit",
    "zero_division_guard": r"(volume|depth|liquidity)\s*[=!]=\s*0|max\(\s*[\w.]+\s*,\s*[0-9.]+e?-?[0-9]*\s*\)",
}


@dataclass
class GuardProfile:
    stop_loss: bool
    spread_guard: bool
    liquidity_guard: bool
    position_limit: bool
    circuit_breaker: bool
    zero_division_guard: bool

    @property
    def score(self) -> int:
        return sum(
            [
                self.stop_loss,
                self.spread_guard,
                self.liquidity_guard,
                self.position_limit,
                self.circuit_breaker,
                self.zero_division_guard,
            ]
        )

    @property
    def missing(self) -> list[str]:
        return [name for name, present in self.as_dict().items() if not present]

    def as_dict(self) -> dict[str, bool]:
        return {
            "stop_loss": self.stop_loss,
            "spread_guard": self.spread_guard,
            "liquidity_guard": self.liquidity_guard,
            "position_limit": self.position_limit,
            "circuit_breaker": self.circuit_breaker,
            "zero_division_guard": self.zero_division_guard,
        }


def detect_guards(code: str) -> GuardProfile:
    """Static inspection only — uploaded strategy code is never executed."""
    lowered = code.lower()
    found = {
        name: bool(re.search(pattern, lowered))
        for name, pattern in GUARD_PATTERNS.items()
    }
    return GuardProfile(**found)
