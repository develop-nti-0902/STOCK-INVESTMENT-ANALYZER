"""
バッチ実行関連のPydanticスキーマ

`JobType` / `JobStatus` Enum と `BatchExecution` 系のスキーマを定義します。
仕様: docs/architecture/layers/service_layer.md
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseRequestSchema, BaseResponseSchema


class JobType(str, Enum):
    SINGLE_STOCK = "SINGLE_STOCK"
    JPX_ALL_STOCKS = "JPX_ALL_STOCKS"
    STOCK_MASTER_UPDATE = "STOCK_MASTER_UPDATE"
    FUNDAMENTAL_DATA = "FUNDAMENTAL_DATA"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchJobParams(BaseModel):
    """バッチジョブのパラメータスキーマ

    代表的なフィールド(`symbol`, `timeframe`など)を定義し、その他は許容する設定にしています。
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    symbol: Optional[str] = Field(
        None, description="Stock symbol (for single-stock jobs)"
    )
    timeframe: Optional[str] = Field(
        None, description="Timeframe (e.g. 1d, 1m)"
    )


class BatchExecutionBase(BaseModel):
    """BatchExecution の基底スキーマ"""

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    job_type: JobType = Field(..., description="Job type")
    status: Optional[JobStatus] = Field(None, description="Job status")
    params: Optional[BatchJobParams] = Field(
        None, description="Job parameters"
    )
    progress: Optional[float] = Field(
        None, description="Progress (0.0–100.0)", ge=0.0, le=100.0
    )
    success_count: Optional[int] = Field(
        None, description="Number of successful items", ge=0
    )
    failed_count: Optional[int] = Field(
        None, description="Number of failed items", ge=0
    )
    error_message: Optional[str] = Field(
        None, description="Error message (if any)"
    )
    started_at: Optional[datetime] = Field(None, description="Start time")
    finished_at: Optional[datetime] = Field(None, description="Finish time")


class BatchExecutionCreate(BaseRequestSchema, BatchExecutionBase):
    """ジョブ作成用スキーマ"""

    # 作成時は status を省略可能（デフォルト PENDING をサーバー側でセット）
    # 注意: ここで `status` の型を上書きしないこと。Base の型定義と整合性を保つため。
    # 作成時はステータスを省略でき、サーバー側でデフォルト（PENDING）を設定します。


class BatchExecutionUpdate(BaseModel):
    """ジョブ更新用スキーマ（部分更新を想定）"""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    status: Optional[JobStatus] = Field(None, description="Job status update")
    progress: Optional[float] = Field(
        None, description="Progress update (0.0–100.0)", ge=0.0, le=100.0
    )
    success_count: Optional[int] = Field(
        None, description="Update number of successful items", ge=0
    )
    failed_count: Optional[int] = Field(
        None, description="Update number of failed items", ge=0
    )
    error_message: Optional[str] = Field(
        None, description="Error message (for update)"
    )


class BatchExecutionResponse(BaseResponseSchema, BatchExecutionBase):
    """APIレスポンス用スキーマ

    BaseResponseSchema が id/created_at/updated_at を提供するため、追加フィールド不要
    """


__all__ = [
    "JobType",
    "JobStatus",
    "BatchJobParams",
    "BatchExecutionBase",
    "BatchExecutionCreate",
    "BatchExecutionUpdate",
    "BatchExecutionResponse",
]
