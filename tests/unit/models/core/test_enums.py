"""Unit tests for enums module."""

from app.models.core.enums import BatchExecutionStatus


def test_batch_execution_status_values():
    """BatchExecutionStatus の各値が期待通りであることを検証する."""
    assert BatchExecutionStatus.PENDING.value == "pending"
    assert BatchExecutionStatus.RUNNING.value == "running"
    assert BatchExecutionStatus.COMPLETED.value == "completed"
    assert BatchExecutionStatus.FAILED.value == "failed"
    assert BatchExecutionStatus.CANCELLED.value == "cancelled"
