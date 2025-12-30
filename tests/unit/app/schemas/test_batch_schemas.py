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


# --- 以下は統合した追加テスト ---


def test_single_stock_request_valid():
    req = batch_schemas.SingleStockDataRequest(
        symbol="7203",
        timeframe="1d",
        start_date="2025-01-01",
        end_date="2025-12-31",
    )
    assert req.symbol == "7203"
    assert req.timeframe == "1d"


def test_single_stock_request_missing_field_raises():
    with pytest.raises(ValidationError):
        batch_schemas.SingleStockDataRequest(
            symbol="7203", timeframe="1d", start_date="2025-01-01"
        )


def test_batch_job_status_and_progress():
    progress = batch_schemas.BatchJobProgress(
        processed=10, total=100, percentage=10.0
    )
    status = batch_schemas.BatchJobStatusResponse(
        job_id="job-1",
        job_type="jpx_all",
        status="running",
        progress=progress,
        started_at="2025-12-27T00:00:00Z",
    )
    assert status.progress.processed == 10


def test_history_response_structure():
    item = batch_schemas.BatchHistoryItem(
        job_id="job-1",
        job_type="jpx_all",
        status="completed",
        started_at="2025-12-27T00:00:00Z",
        completed_at="2025-12-27T00:10:00Z",
    )
    history = batch_schemas.BatchHistoryResponse(
        items=[item], total=1, limit=10, offset=0, count=1
    )
    assert history.count == 1
