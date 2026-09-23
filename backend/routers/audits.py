import logging

from fastapi import APIRouter, Query

from contracts import AuditReport, AuditRequest
from engine.store import set_verdict
from engine.strategy import detect_guards
from llm.audit import FALLBACK, audit
from llm.nebius import NebiusError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/audits", tags=["audits"])


@router.post("", response_model=AuditReport)
async def audit_run(
    request: AuditRequest,
    use_mock: bool = Query(False, alias="use_mock"),
) -> AuditReport:
    guards = detect_guards(request.code or "").as_dict()

    try:
        report, telemetry = await audit(request, guards, use_mock=use_mock)
    except NebiusError as exc:
        logger.warning("audit fell back to fixture: %s", exc)
        set_verdict(request.id, FALLBACK.verdict)
        return FALLBACK

    logger.info(
        "audited %s via %s: %s (%d)",
        request.id,
        telemetry.get("model"),
        report.verdict,
        report.score,
    )
    set_verdict(request.id, report.verdict)
    return report
