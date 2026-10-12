from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class BacktestRequest(BaseModel):
    code: str
    scenario_prompt: str
    starting_capital: float
    use_mock: bool = False

class BacktestResponse(BaseModel):
    strategy_verdict: str
    risk_score: int
    failure_point: Optional[str] = None
    vulnerabilities: List[str]
    simulated_market_trace: List[Dict[str, Any]]
    refactored_code: str
    diff: str
    benchmark_stats: Dict[str, Any]
