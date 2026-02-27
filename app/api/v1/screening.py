"""Screening API router.

Minimal endpoints to trigger the `SimpleScreeningService` for screening.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.services import get_screening_service
from app.services.screening.simple_screening_service import SimpleScreeningService

router = APIRouter(tags=["screening"])


class RunRequest(BaseModel):
    sec_codes: Optional[List[str]] = None
    evaluation_date: date


class RunResponse(BaseModel):
    message: str


class EvaluateResponse(BaseModel):
    sec_code: str
    pass_required: bool
    total_score: int
    score_dividend: int
    score_eps: int
    score_stability: int
    score_profitability: int
    status: str
    failed_conditions: List[str]
    fiscal_year_end: Optional[date]


@router.post("/run", response_model=RunResponse)
async def run_screening(
    req: RunRequest, service: SimpleScreeningService = Depends(get_screening_service)
) -> RunResponse:
    """Run screening for given symbols (or all when `sec_codes` is None)."""
    await service.run(req.sec_codes, req.evaluation_date)
    return RunResponse(message="Screening completed")


@router.get("/evaluate/{sec_code}", response_model=EvaluateResponse)
async def evaluate(
    sec_code: str,
    evaluation_date: Optional[date] = None,
    service: SimpleScreeningService = Depends(get_screening_service),
) -> EvaluateResponse:
    """Evaluate a single symbol and return the screening result."""
    if evaluation_date is None:
        evaluation_date = date.today()
    res = await service.evaluate(sec_code, evaluation_date)
    return EvaluateResponse(
        sec_code=res.sec_code,
        pass_required=res.pass_required,
        total_score=res.total_score,
        score_dividend=res.score_dividend,
        score_eps=res.score_eps,
        score_stability=res.score_stability,
        score_profitability=res.score_profitability,
        status=res.status,
        failed_conditions=res.failed_conditions,
        fiscal_year_end=res.fiscal_year_end,
    )
