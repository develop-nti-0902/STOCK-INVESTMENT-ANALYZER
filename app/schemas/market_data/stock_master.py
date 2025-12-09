"""
銘柄マスタスキーマ

JPXから取得する銘柄マスタデータのPydanticスキーマを定義します。
仕様書: docs/architecture/layers/service_layer.md 3.2.2章
"""

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class StockMasterRaw(BaseModel):
    """
    JPXから取得した銘柄マスタの生データスキーマ

    JPXの銘柄一覧エクセルファイルから取得したデータを正規化する前の形式です。
    データソースの変動に対応するため、全てのフィールドをOptionalとしています。
    """

    model_config = ConfigDict(
        # 任意フィールドの型チェックを厳密に
        validate_assignment=True,
        # 不明なフィールドを許可（データソースの変化に対応）
        extra="allow",
        # フィールド名とエイリアスの両方を受け入れる
        populate_by_name=True,
    )

    # 日本語カラム名（JPXエクセルファイルの実際のカラム名）
    # Pydanticではフィールド名をPythonの識別子として定義し、aliasで元のカラム名を指定
    # Excel読み込み時に数値型として読み込まれる可能性があるため、Union[str, int]で定義
    date: Optional[Union[str, int]] = Field(
        default=None, alias="日付", description="データ取得日"
    )
    code: Optional[Union[str, int]] = Field(
        default=None, alias="コード", description="銘柄コード"
    )
    name: Optional[str] = Field(
        default=None, alias="銘柄名", description="銘柄名"
    )
    market: Optional[str] = Field(
        default=None, alias="市場・商品区分", description="市場・商品区分"
    )
    # 33業種コード・33業種区分
    sector_code_33: Optional[Union[str, int]] = Field(
        default=None, alias="33業種コード", description="33業種コード"
    )
    sector_name_33: Optional[str] = Field(
        default=None, alias="33業種区分", description="33業種区分名"
    )
    # 17業種コード・17業種区分
    sector_code_17: Optional[Union[str, int]] = Field(
        default=None, alias="17業種コード", description="17業種コード"
    )
    sector_name_17: Optional[str] = Field(
        default=None, alias="17業種区分", description="17業種区分名"
    )
    scale_code: Optional[Union[str, int]] = Field(
        default=None, alias="規模コード", description="規模コード"
    )
    scale_category: Optional[str] = Field(
        default=None, alias="規模区分", description="規模区分"
    )


class StockMasterNormalized(BaseModel):
    """
    正規化された銘柄マスタスキーマ

    StockMasterモデル（DBテーブル）に対応する形式です。
    必須フィールドのみをnullableとし、データ品質を保証します。
    """

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        extra="forbid",
    )

    stock_code: str = Field(
        ..., description="銘柄コード", min_length=4, max_length=10
    )
    stock_name: str = Field(..., description="銘柄名", min_length=1)
    market_category: Optional[str] = Field(
        default=None, description="市場区分"
    )
    sector_code_33: Optional[str] = Field(
        default=None, description="33業種コード"
    )
    sector_name_33: Optional[str] = Field(
        default=None, description="33業種区分名"
    )
    sector_code_17: Optional[str] = Field(
        default=None, description="17業種コード"
    )
    sector_name_17: Optional[str] = Field(
        default=None, description="17業種区分名"
    )
    scale_code: Optional[str] = Field(default=None, description="規模コード")
    scale_category: Optional[str] = Field(default=None, description="規模区分")
    data_date: Optional[str] = Field(
        default=None, description="データ日付（YYYYMMDD形式）", max_length=8
    )
    is_active: int = Field(
        default=1, description="有効フラグ（1:有効, 0:無効）"
    )


class StockMasterResponse(StockMasterNormalized):
    """
    銘柄マスタレスポンススキーマ（API返却用）

    IDとタイムスタンプを含むAPI返却用のスキーマです。
    """

    id: Optional[int] = Field(default=None, description="レコードID")


__all__ = [
    "StockMasterRaw",
    "StockMasterNormalized",
    "StockMasterResponse",
]
