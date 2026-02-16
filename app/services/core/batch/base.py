"""サービス層バッチの基底クラスとコンテキスト.

このモジュールはサービス固有の `batch.py` が継承して使う基底を提供します。
設計方針として本モジュールはサービス固有の型に依存しないようにし、
インターフェース（メソッド名）により疎結合で呼び出せるようにします。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseBatchRunner:
    """サービス層向けバッチランナー基底クラス.

    継承クラスは `run(*args, **kwargs)` を実装して処理サマリ辞書を返してください。
    基底は分割や進捗コールバックのユーティリティを提供します。
    """

    def __init__(
        self,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """初期化.

        Args:
            progress_callback: 進捗更新コールバック（任意）
        """
        self.progress_callback = progress_callback

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """実行エントリポイント（継承先で実装）."""
        raise NotImplementedError()

    @staticmethod
    def chunk_iter(items: List[Any], size: int) -> Iterable[List[Any]]:
        """アイテムリストを指定サイズで分割するジェネレータ."""
        for i in range(0, len(items), size):
            yield items[i : i + size]

    async def _update_ctx_progress(self, ctx: Any, **kwargs: Any) -> None:
        """コンテキスト（batch job context）へ進捗更新を試みる.

        ctx はサービス側が返すオブジェクトで、`update_progress` を持つことが期待される。
        なければ安全に無視します。
        """
        if not ctx:
            return

        updater = getattr(ctx, "update_progress", None)
        try:
            if callable(updater):
                result = updater(**kwargs)
                # updater が coroutine を返す/実装している場合に await
                if hasattr(result, "__await__"):
                    await result
        except Exception:
            logger.exception("Failed to update batch progress")
