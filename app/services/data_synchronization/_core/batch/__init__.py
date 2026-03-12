"""サービス層用バッチ共通モジュール.

各サービス配下の `batch.py` が継承して使う基底を提供します。
"""

from app.services.data_synchronization._core.batch.base import BaseBatchRunner

__all__ = ["BaseBatchRunner"]
