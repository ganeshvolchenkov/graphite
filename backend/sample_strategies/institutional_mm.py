import math
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class OrderBookLevel:
    price: float
    size: float


@dataclass
class OrderBook:
    timestamp: float
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]

    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else float("inf")

    @property
    def total_bid_depth(self) -> float:
        return sum(level.size for level in self.bids[:5])

    @property
    def total_ask_depth(self) -> float:
        return sum(level.size for level in self.asks[:5])


class FlashCrashVulnerableMM:
    """High-frequency market maker using inventory skew and depth elasticity."""

    def __init__(self, target_inventory: float = 0.0, risk_aversion: float = 0.1):
        self.gamma = risk_aversion
        self.target_inv = target_inventory
        self.current_inventory = 0.0
        self.cash = 1_000_000.0
        self.realized_pnl = 0.0

    def compute_quotes(self, book: OrderBook, time_remaining: float = 1.0) -> Dict:
        if not book.bids or not book.asks:
            raise RuntimeError("Order book completely empty: Exchange Feed Halt")

        mid_price = (book.best_bid + book.best_ask) / 2.0
        bid_depth = book.total_bid_depth
        ask_depth = book.total_ask_depth

        reservation_price = mid_price - (self.current_inventory - self.target_inv) * self.gamma

        liquidity_elasticity = bid_depth / (ask_depth + 1e-9)
        half_spread = (1.0 / self.gamma) * math.log(1.0 + (1.0 / bid_depth))

        optimal_bid = min(reservation_price - half_spread, book.best_bid)
        optimal_ask = max(reservation_price + half_spread, book.best_ask)

        depth_imbalance = (ask_depth - bid_depth) / (bid_depth + ask_depth)
        position_scale = 1.0 / (bid_depth / 500.0)
        quote_size = max(10, int(100 * position_scale * (1.0 + depth_imbalance)))

        return {
            "bid_price": round(optimal_bid, 4),
            "ask_price": round(optimal_ask, 4),
            "quote_size": quote_size,
            "mid_price": mid_price,
            "bid_depth": bid_depth,
        }

    def on_market_fill(self, fill_price: float, fill_size: float, side: str):
        if side == "BUY":
            self.current_inventory += fill_size
            self.cash -= fill_price * fill_size
        elif side == "SELL":
            self.current_inventory -= fill_size
            self.cash += fill_price * fill_size
