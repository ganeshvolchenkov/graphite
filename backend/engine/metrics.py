import statistics

from contracts import Metrics

TRADING_DAYS = 252


def build_metrics(
    *,
    equity: float,
    start_equity: float,
    max_drawdown: float,
    returns: list[float],
    slippage_costs: list[float],
    trades: int,
    wins: int,
    exposure: int,
) -> Metrics:
    pnl = equity - start_equity
    stdev = statistics.pstdev(returns) if len(returns) > 1 else 0.0
    sharpe = (statistics.fmean(returns) / stdev * (TRADING_DAYS**0.5)) if stdev else 0.0

    return Metrics(
        pnl=round(pnl, 2),
        pnl_pct=round(pnl / start_equity * 100.0, 2),
        max_drawdown_pct=round(max_drawdown, 2),
        sharpe=round(sharpe, 2),
        trades=trades,
        slippage_bps=round(statistics.fmean(slippage_costs), 2) if slippage_costs else 0.0,
        win_rate_pct=round(wins / trades * 100.0, 1) if trades else 0.0,
        exposure_minutes=exposure,
        final_equity=round(equity, 2),
    )
