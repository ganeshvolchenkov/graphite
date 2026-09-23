"""Strategy execution worker. Runs in an isolated subprocess, never in the API process.

Reads {code, rows} as JSON on stdin, writes {ticks, fills, quotes, stdout, error} on
stdout. The strategy namespace comes from safeexec (real Python minus filesystem and
process access, with an import allowlist). Anything the strategy prints is captured so it
cannot corrupt the JSON channel.
"""

import contextlib
import io
import json
import sys

from safeexec import build_namespace

START_EQUITY = 1_000_000.0
MAX_STEPS = 5_000


class Level:
    __slots__ = ("price", "size")

    def __init__(self, raw):
        self.price = raw["price"]
        self.size = raw["size"]


class Bar:
    __slots__ = (
        "index", "t_ms", "clock", "phase", "price", "mid", "spread_bps", "spread_pips",
        "volatility_pct", "atr", "rolling_high", "rolling_low", "stale", "halted",
    )

    def __init__(self, row):
        self.index = row["index"]
        self.t_ms = row["t_ms"]
        self.clock = row["clock"]
        self.phase = row["phase"]
        self.price = row["price"]
        self.mid = row["price"]
        self.spread_bps = row["spread_bps"]
        self.spread_pips = row["spread_pips"]
        self.volatility_pct = row["volatility_pct"]
        self.atr = row["atr"]
        self.rolling_high = row["rolling_high"]
        self.rolling_low = row["rolling_low"]
        self.stale = row["stale"]
        self.halted = row["halted"]


class Book:
    __slots__ = (
        "bid", "ask", "bids", "asks", "depth_bid", "depth_ask", "imbalance",
        "liquidity_pct", "spread_bps", "crossed", "toxic", "toxic_direction",
    )

    def __init__(self, row):
        self.bid = row["bid"]
        self.ask = row["ask"]
        self.bids = [Level(level) for level in row["bids"]]
        self.asks = [Level(level) for level in row["asks"]]
        self.depth_bid = row["depth_bid"]
        self.depth_ask = row["depth_ask"]
        self.imbalance = row["imbalance"]
        self.liquidity_pct = row["liquidity_pct"]
        self.spread_bps = row["spread_bps"]
        self.crossed = row["crossed"]
        self.toxic = row["toxic"]
        self.toxic_direction = row["toxic_direction"]

    @property
    def depth(self):
        return int(self.depth_bid + self.depth_ask)


class Account:
    def __init__(self):
        self.equity = START_EQUITY
        self.cash = START_EQUITY
        self.position = 0.0
        self.entry_price = 0.0
        self.trades = 0
        self.passive_fills = 0
        self.adverse_fills = 0
        self._row = None
        self._prev_price = 0.0
        self._fills = []
        self._quotes = []

    @property
    def inventory(self):
        return self.position

    @property
    def unhedged_delta(self):
        return round(self.position * self._row["price"], 2) if self._row else 0.0

    @property
    def adverse_fill_rate(self):
        return round(self.adverse_fills / self.passive_fills * 100.0, 2) if self.passive_fills else 0.0

    def _cross_price(self, side):
        row = self._row
        effective = row["spread_bps"] * (1.0 + (100.0 - row["liquidity_pct"]) / 100.0)
        edge = row["price"] * (effective / 2.0) / 10_000.0
        return row["price"] + edge if side == "buy" else row["price"] - edge

    def _record(self, side, size, price, passive):
        self._fills.append(
            {"index": self._row["index"], "side": side, "size": size,
             "price": price, "passive": passive}
        )

    def buy(self, size):
        size = float(size)
        if size <= 0:
            return
        price = self._cross_price("buy")
        self.cash -= size * price
        if self.position <= 0:
            self.entry_price = price
        self.position += size
        self.trades += 1
        self._record("buy", size, price, False)

    def sell(self, size):
        size = float(size)
        if size <= 0:
            return
        price = self._cross_price("sell")
        self.cash += size * price
        self.position -= size
        self.trades += 1
        self._record("sell", size, price, False)

    def flatten(self):
        if self.position > 0:
            self.sell(self.position)
        elif self.position < 0:
            self.buy(-self.position)
        self.entry_price = 0.0

    def _passive_buy(self, price, size, adverse):
        self.cash -= size * price
        self.position += size
        self.trades += 1
        self.passive_fills += 1
        self.adverse_fills += 1 if adverse else 0
        self._record("buy", size, float(price), True)

    def _passive_sell(self, price, size, adverse):
        self.cash += size * price
        self.position -= size
        self.trades += 1
        self.passive_fills += 1
        self.adverse_fills += 1 if adverse else 0
        self._record("sell", size, float(price), True)

    def quote(self, bid_price, ask_price, size):
        """Post a two-sided passive quote.

        Counterparties trade in the direction the market is moving, so a falling market
        hits your bid and leaves you long into the move. That is adverse selection, and
        it is what punishes a maker who keeps quoting tight through a dislocation.
        """
        size = float(size)
        if size <= 0:
            return
        row = self._row
        self._quotes.append(
            {"index": row["index"], "bid": float(bid_price), "ask": float(ask_price), "size": size}
        )
        if row["crossed"] or row["halted"]:
            return

        # Only a move well outside normal tick noise represents informed, one-way flow.
        # atr spans ~sqrt(14) steps, so atr*0.4 is roughly 1.5 standard tick moves.
        drift = row["price"] - self._prev_price
        noise = row["atr"] * 0.4
        toxic = row["toxic"]
        marketable_bid = bid_price >= row["bid"]
        marketable_ask = ask_price <= row["ask"]

        if toxic > 0:
            # Informed one-way flow only lifts the side that leaves you holding the loser.
            if row["toxic_direction"] == "sell" and marketable_bid:
                self._passive_buy(bid_price, size, adverse=True)
            elif row["toxic_direction"] == "buy" and marketable_ask:
                self._passive_sell(ask_price, size, adverse=True)
            return

        if drift < -noise:
            if marketable_bid:
                self._passive_buy(bid_price, size, adverse=True)
        elif drift > noise:
            if marketable_ask:
                self._passive_sell(ask_price, size, adverse=True)
        else:
            # Two-way flow in a quiet tick: both sides print and you earn the spread.
            if marketable_bid:
                self._passive_buy(bid_price, size, adverse=False)
            if marketable_ask:
                self._passive_sell(ask_price, size, adverse=False)

    def stop_loss_hit(self, distance):
        if not self.position or not self.entry_price:
            return False
        return self._row["price"] <= self.entry_price - float(distance)


def load_strategy(code):
    namespace = build_namespace()
    exec(compile(code, "<strategy>", "exec"), namespace)  # noqa: S102 - restricted, isolated
    fn = namespace.get("on_tick")
    if not callable(fn):
        raise ValueError(
            "strategy must define on_tick(bar, book, account) - "
            "use /api/strategies/adapt to generate an adapter for a different interface"
        )
    return fn


def main():
    payload = json.loads(sys.stdin.read())
    rows = payload["rows"]
    account = Account()
    error = None
    captured = io.StringIO()
    channel = sys.stdout

    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            on_tick = load_strategy(payload["code"])
    except Exception as exc:
        json.dump(
            {"ticks": [], "fills": [], "quotes": [], "stdout": captured.getvalue()[:4000],
             "error": {"type": type(exc).__name__, "message": str(exc), "index": None}},
            channel,
        )
        return

    ticks = []
    for step, row in enumerate(rows):
        if step > MAX_STEPS:
            break
        account._prev_price = rows[step - 1]["price"] if step else row["price"]
        account._row = row
        if error is None:
            try:
                with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                    on_tick(Bar(row), Book(row), account)
            except Exception as exc:
                error = {"type": type(exc).__name__, "message": str(exc), "index": row["index"]}

        equity = account.cash + account.position * row["price"]
        account.equity = equity
        ticks.append(
            {
                "index": row["index"],
                "position": round(account.position, 4),
                "trades": account.trades,
                "equity": round(equity, 4),
                "entry_price": round(account.entry_price, 6),
                "passive_fills": account.passive_fills,
                "adverse_fills": account.adverse_fills,
            }
        )

    json.dump(
        {"ticks": ticks, "fills": account._fills, "quotes": account._quotes,
         "stdout": captured.getvalue()[:4000], "error": error},
        channel,
    )


if __name__ == "__main__":
    main()
