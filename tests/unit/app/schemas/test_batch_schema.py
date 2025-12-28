from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import batch as batch_schemas


def test_jobtype_enum_values():
    assert batch_schemas.JobType.SINGLE_STOCK.value == "SINGLE_STOCK"
    assert "JPX_ALL_STOCKS" in [e.value for e in batch_schemas.JobType]


def test_jobstatus_enum_values():
    assert batch_schemas.JobStatus.PENDING.value == "PENDING"
    assert batch_schemas.JobStatus.FAILED in batch_schemas.JobStatus


def test_batch_job_params_allows_extra():
    params = batch_schemas.BatchJobParams(
        symbol="7203.T", timeframe="1d", extra_field="allowed"
    )
    assert params.symbol == "7203.T"
    assert params.timeframe == "1d"
    assert getattr(params, "extra_field") == "allowed"


def test_batch_execution_create_minimal():
    be = batch_schemas.BatchExecutionCreate(
        job_type=batch_schemas.JobType.SINGLE_STOCK
    )
    assert be.job_type == batch_schemas.JobType.SINGLE_STOCK
    assert be.status is None


def test_progress_bounds_validation():
    with pytest.raises(ValidationError):
        batch_schemas.BatchExecutionBase(
            job_type=batch_schemas.JobType.SINGLE_STOCK,
            status=batch_schemas.JobStatus.PENDING,
            progress=150.0,
        )
    with pytest.raises(ValidationError):
        batch_schemas.BatchExecutionBase(
            job_type=batch_schemas.JobType.SINGLE_STOCK,
            status=batch_schemas.JobStatus.PENDING,
            progress=-1.0,
        )


def test_update_extra_forbid():
    with pytest.raises(ValidationError):
        batch_schemas.BatchExecutionUpdate(unknown_field=1)


def test_response_includes_base_fields():
    now = datetime.now(timezone.utc)
    resp = batch_schemas.BatchExecutionResponse(
        id=1,
        job_type=batch_schemas.JobType.JPX_ALL_STOCKS,
        status=batch_schemas.JobStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    assert resp.id == 1
    assert resp.job_type == batch_schemas.JobType.JPX_ALL_STOCKS
