"""株式マスタの変換ユーティリティモジュール.

Pydantic モデルをリポジトリ保存用の辞書に変換するコンバータを提供します.
"""

from typing import List

from app.schemas.market_data.stock_master import StockMasterNormalized


class StockMasterConverter:
    """Pydantic の `StockMasterNormalized` を保存用辞書に変換するコンバータ.

    将来的なフィールドマッピングや正規化を中央で管理するために
    変換処理を集約します.
    """

    def to_records(self, models: List[StockMasterNormalized]) -> List[dict]:
        """Pydanticモデルのリストを保存用辞書のリストに変換します.

        Args:
            models: `StockMasterNormalized`インスタンスのリスト

        Returns:
            list[dict]: リポジトリの`bulk_upsert`に渡す準備ができたレコード
        """
        records: List[dict] = []
        for m in models:
            # 一貫性を保つため `model_dump` を使用して辞書化する
            records.append(m.model_dump(exclude_none=True))

        return records


__all__ = ["StockMasterConverter"]
