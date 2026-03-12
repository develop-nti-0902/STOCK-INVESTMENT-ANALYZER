"""モデルで使用するEnum定義."""

from enum import Enum


class BatchExecutionStatus(str, Enum):
    """バッチ実行ステータス.

    Attributes:
        PENDING: 未実行 - バッチジョブが作成されたが、まだ開始されていない状態
        RUNNING: 実行中 - バッチジョブが現在実行中の状態
        COMPLETED: 完了 - バッチジョブが正常に完了した状態
        FAILED: 失敗 - バッチジョブが失敗した状態
        CANCELLED: キャンセル - バッチジョブがキャンセルされた状態
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


__all__ = ["BatchExecutionStatus"]
