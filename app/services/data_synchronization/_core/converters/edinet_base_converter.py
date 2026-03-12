"""EDINET 向けの変換ユーティリティをまとめた基底コンバータ.

このモジュールは EDINET 固有の入力正規化やヘルパーを提供し、
個別のシートコンバータから共通処理を取り除くことを目的とします。
"""

from __future__ import annotations

from abc import abstractmethod
from decimal import Decimal
from typing import Any, Dict, Generic, Optional, TypeVar

from app.services.data_synchronization._core.converters.base_converter import BaseConverter

# ジェネリック型パラメータ
T = TypeVar("T")


class EdinetBaseConverter(BaseConverter[T], Generic[T]):
    """EDINET 向け共通ヘルパーを提供する基底クラス.

    サブクラスは `to_pydantic` / `from_pydantic` を実装する点は変わりませんが、
    以下のようなユーティリティを提供します:
    - `to_decimal`: 数値を Decimal に安全変換
    - `fiscal_year_from_period`: period 文字列/日付から会計年度を抽出
    - `extract_metadata`: パーサ出力から共通メタデータを取り出す
    """

    def to_decimal(self, value: Any) -> Optional[Decimal]:
        """値を Decimal に変換する。変換失敗時は None を返す."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def fiscal_year_from_period(self, period_value: Any) -> Optional[int]:
        """period（例: '2023-03-31' や date オブジェクト）から年度（年）を返す。

        解析不能な場合は None を返す。
        """
        if period_value is None:
            return None
        try:
            # 文字列の場合は先頭の4桁を抽出
            if isinstance(period_value, str):
                return int(str(period_value).split("-", maxsplit=1)[0])
            # date / datetime の場合は year を返す
            year = getattr(period_value, "year", None)
            if year is not None:
                return int(year)
        except Exception:
            return None
        return None

    def extract_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """パーサ出力からよく使われるメタデータを抜き出して返す.

        返却辞書には少なくとも `doc_id`, `sec_code`, `submission_date`, `filer_name` を含める。
        """
        return {
            "doc_id": data.get("doc_id", ""),
            "sec_code": data.get("sec_code", ""),
            "submission_date": data.get("submission_date"),
            "filer_name": data.get("filer_name"),
        }

    # --- Template methods for common converter operations ---
    def to_pydantic(self, data: Dict[str, Any]) -> T:
        """共通の to_pydantic テンプレート実装.

        - メタデータ抽出
        - period_end / period_end_date の解決
        - fiscal_year の算出
        - サブクラスの `_normalize_fields` と `_build_model` を利用してモデルを作成
        """
        meta = self.extract_metadata(data)
        # period の優先キーを解決
        period = data.get("period_end") or data.get("period_end_date")
        if not period:
            raise ValueError("period_end or period_end_date is required")

        fiscal_year = self.fiscal_year_from_period(period)

        # サブクラス固有のフィールド正規化
        extra = self._normalize_fields(data)

        model_kwargs: Dict[str, Any] = {
            "doc_id": meta.get("doc_id", ""),
            "sec_code": meta.get("sec_code", ""),
            "submission_date": meta.get("submission_date"),
            "period_end_date": period,
            "fiscal_year": fiscal_year,
        }
        model_kwargs.update(extra)

        return self._build_model(model_kwargs)

    def to_saver_records(self, models: list[T]) -> list[Dict[str, Any]]:
        """デフォルト実装: `from_pydantic` を利用してバッチ変換する。"""
        return [self.from_pydantic(m) for m in models]

    def _to_saver_record(self, model: T) -> Dict[str, Any]:
        """デフォルトの saver レコード生成: Pydantic の `dict()` を使う。"""
        # Pydantic BaseModel を想定
        try:
            if hasattr(model, "model_dump"):
                return getattr(model, "model_dump")()
            return getattr(model, "dict")()
        except Exception:
            # フォールバック: __dict__ を使う
            return {k: getattr(model, k) for k in dir(model) if not k.startswith("_")}

    def from_pydantic(self, model: T) -> Dict[str, Any]:
        """デフォルト実装: `_to_saver_record` のラッパー。"""
        return self._to_saver_record(model)

    def from_dataframe(self, df: Any, *args, **kwargs) -> list[T]:
        """デフォルトでは未実装。必要なら各サブクラスでオーバーライド。"""
        raise NotImplementedError(
            "from_dataframe is not implemented for EdinetBaseConverter subclasses."
        )

    # --- 抽象メソッド: サブクラスで実装する ---
    def _normalize_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """サブクラス固有のフィールド正規化処理。

        デフォルトは元データをそのまま返すが、数値を Decimal に変換するなどの処理は
        サブクラスでここをオーバーライドして実装すること。
        """
        return dict(data)

    @abstractmethod
    def _build_model(self, model_kwargs: Dict[str, Any]) -> T:
        """model_kwargs から Pydantic モデル `T` を構築して返すことをサブクラスに要求する。"""
        raise NotImplementedError


__all__ = ["EdinetBaseConverter"]
