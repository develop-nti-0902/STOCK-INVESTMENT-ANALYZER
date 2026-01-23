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


def test_jpx_all_multi_sequence_request_default_batch_size():
    """JPXAllMultiSequenceRequestのデフォルトbatch_sizeが50であることを確認."""
    req = batch_schemas.JPXAllMultiSequenceRequest()
    assert req.batch_size == 50


def test_jpx_all_multi_sequence_request_custom_batch_size():
    """JPXAllMultiSequenceRequestがカスタムbatch_sizeを受け付けることを確認."""
    req = batch_schemas.JPXAllMultiSequenceRequest(batch_size=100)
    assert req.batch_size == 100


def test_jpx_all_multi_sequence_request_batch_size_bounds():
    """batch_sizeが範囲外の値を拒否することを確認."""
    with pytest.raises(ValidationError):
        batch_schemas.JPXAllMultiSequenceRequest(batch_size=0)

    with pytest.raises(ValidationError):
        batch_schemas.JPXAllMultiSequenceRequest(batch_size=201)


def test_timeframe_result_creation():
    """TimeframeResultが正しく作成できることを確認."""
    result = batch_schemas.TimeframeResult(
        timeframe="1d",
        status="completed",
        success_count=100,
        failed_count=5,
        error_message=None,
        started_at="2026-01-17T00:00:00",
        finished_at="2026-01-17T00:10:00",
    )
    assert result.timeframe == "1d"
    assert result.status == "completed"
    assert result.success_count == 100
    assert result.failed_count == 5


def test_jpx_all_multi_sequence_response_creation():
    """JPXAllMultiSequenceResponseが正しく作成できることを確認."""
    response = batch_schemas.JPXAllMultiSequenceResponse(
        job_id="123",
        overall_status="COMPLETED",
        results=[
            batch_schemas.TimeframeResult(
                timeframe="1d",
                status="completed",
                success_count=100,
                failed_count=0,
            ),
            batch_schemas.TimeframeResult(
                timeframe="1m",
                status="completed",
                success_count=95,
                failed_count=5,
            ),
        ],
    )
    assert response.job_id == "123"
    assert response.overall_status == "COMPLETED"
    assert len(response.results) == 2
    assert response.results[0].timeframe == "1d"
    assert response.results[1].timeframe == "1m"
