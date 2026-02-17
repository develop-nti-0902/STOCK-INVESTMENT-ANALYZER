"""サービス層用バッチ共通モジュール.

各サービス配下の `batch.py` が継承して使う基底を提供します。
"""

from .base import BaseBatchRunner

__all__ = ["BaseBatchRunner"]
