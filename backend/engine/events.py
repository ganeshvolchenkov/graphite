from contracts import MarketEvent, ScenarioScript

from .sandbox import ExecutionResult


def _note(row: dict, severity: str, message: str) -> MarketEvent:
    return MarketEvent(clock=row["clock"], severity=severity, message=message)


def regime_events(rows: list[dict], script: ScenarioScript) -> dict[int, MarketEvent]:
    """One event per notable market-state transition, keyed by row index."""
    events: dict[int, MarketEvent] = {}
    seen: set[str] = set()
    unit = script.instrument.quote_unit
    baseline = script.baseline_bps()

    for row in rows:
        index = row["index"]

        if row["phase"] == "shock" and "shock" not in seen:
            seen.add("shock")
            events[index] = _note(row, "warn", "Shock regime entered.")

        if row["spread_bps"] > baseline * 5 and "spread" not in seen:
            seen.add("spread")
            shown = f"{row['spread_pips']:.1f} pips" if unit == "pip" else f"{row['spread_bps']:.1f} bps"
            events[index] = _note(row, "critical", f"Spread blew out to {shown}.")

        if row["crossed"] and "crossed" not in seen:
            seen.add("crossed")
            events[index] = _note(
                row, "critical",
                f"Book CROSSED: bid {row['bid']:.5f} above ask {row['ask']:.5f}.",
            )

        if row["stale"] and "stale" not in seen:
            seen.add("stale")
            events[index] = _note(row, "critical", "Market data feed frozen — quotes now stale.")

        if row["toxic"] > 0 and "toxic" not in seen:
            seen.add("toxic")
            events[index] = _note(
                row, "warn",
                f"Toxic {row['toxic_direction']} flow detected (intensity {row['toxic']:.2f}).",
            )

        if row["depth_bid"] < row["depth_ask"] * 0.2 and "skew" not in seen:
            seen.add("skew")
            events[index] = _note(
                row, "critical",
                f"Bid side evaporated: depth {row['depth_bid']:.0f} vs ask {row['depth_ask']:.0f}.",
            )

        if row["halted"] and "halted" not in seen:
            seen.add("halted")
            events[index] = _note(row, "warn", "Trading halted.")

    return events


def strategy_events(execution: ExecutionResult, rows: list[dict]) -> dict[int, MarketEvent]:
    events: dict[int, MarketEvent] = {}

    for fill in execution.fills:
        row = rows[fill["index"]]
        verb = "Bought" if fill["side"] == "buy" else "Sold"
        kind = "passive quote filled" if fill["passive"] else "market order"
        events[fill["index"]] = _note(
            row, "info",
            f"{verb} {fill['size']:.0f} @ {fill['price']:.5f} ({kind}).",
        )

    adverse = [row for row in execution.ticks if row.get("adverse_fills")]
    if adverse:
        first = adverse[0]
        row = rows[min(first["index"], len(rows) - 1)]
        events[row["index"]] = _note(
            row, "critical",
            "Adversely selected: informed flow lifted the resting quote.",
        )

    if execution.error:
        error = execution.error
        index = error["index"] if error["index"] is not None else 0
        row = rows[min(index, len(rows) - 1)]
        events[row["index"]] = _note(
            row, "critical",
            f"Strategy raised {error['type']}: {error['message']} — execution halted.",
        )

    return events
