import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from mock_data import MOCK_RESPONSE
from routers import audits, benchmark, runs, scenarios, simulations, strategies
from schemas import BacktestRequest, BacktestResponse
from services import audit_code_and_generate_diff, generate_synthetic_market_tape

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="StressTest API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Cache-Control"],
    expose_headers=["Content-Type"],
)

app.include_router(scenarios.router)
app.include_router(simulations.router)
app.include_router(audits.router)
app.include_router(strategies.router)
app.include_router(runs.router)
app.include_router(benchmark.router)


STATIC = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    """Opening the bare URL should land on something, not a 404."""
    return RedirectResponse(url="/dashboard")


@app.get("/health")
def health_check():
    return {"status": "ok", "engine": "Nebius Token Factory Ready"}


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC / "dashboard.html", media_type="text/html")


@app.get("/brief", include_in_schema=False)
def brief() -> FileResponse:
    """The frontend handoff brief, with a copy button for the Lovable prompt."""
    return FileResponse(STATIC / "brief.html", media_type="text/html")


@app.get("/fixtures.json", include_in_schema=False)
def fixtures() -> FileResponse:
    """Captured responses for every endpoint, so the frontend can be built offline."""
    return FileResponse(STATIC / "fixtures.json", media_type="application/json")

@app.post("/api/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    if request.use_mock:
        return MOCK_RESPONSE
    
    # 1. Generate synthetic market tape based on the scenario
    tape = await generate_synthetic_market_tape(request.scenario_prompt)
    
    # 2. Audit code and generate diff using the generated tape
    audit_results = await audit_code_and_generate_diff(request.code, tape)
    
    # Construct response
    return BacktestResponse(
        strategy_verdict=audit_results.get("strategy_verdict", "ERROR"),
        risk_score=audit_results.get("risk_score", 100),
        failure_point=audit_results.get("failure_point"),
        vulnerabilities=audit_results.get("vulnerabilities", []),
        simulated_market_trace=tape,
        refactored_code=audit_results.get("refactored_code", request.code),
        diff=audit_results.get("diff", ""),
        benchmark_stats=audit_results.get("benchmark_stats", {})
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)