from schemas import BacktestResponse

MOCK_RESPONSE = BacktestResponse(
    strategy_verdict="FAIL",
    risk_score=95,
    failure_point="Liquidity Freeze - ZeroDivisionError at line 42",
    vulnerabilities=[
        "No handling for zero volume during flash crashes",
        "Infinite loop potential in retry logic"
    ],
    simulated_market_trace=[
        {"time": "09:30", "event": "Market Open", "price": 150.0, "volume": 1000},
        {"time": "10:15", "event": "Liquidity Drain", "price": 145.0, "volume": 0},
        {"time": "10:16", "event": "Crash", "price": 0.0, "volume": 0}
    ],
    refactored_code="def execute_trade(volume):\n    if volume == 0:\n        return 'Aborted'\n    # original logic...",
    diff="--- original\n+++ refactored\n- return price / volume\n+ if volume == 0: return 0\n+ return price / volume",
    benchmark_stats={
        "max_drawdown": "-100%",
        "sharpe_ratio": -5.0
    }
)
