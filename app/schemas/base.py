"""
スキーマ層 - 基底クラス

全てのPydanticスキーマの基底となるクラスを定義する。
共通フィールド（id, created_at, updated_at）を提供し、リクエスト/レスポンスの雛形を提供する。
仕様書: docs/architecture/layers/service_layer.md 7章、data_access_layer.md 3.1章
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """
    スキーマ基底クラス（共通フィールド提供）

    全てのPydanticスキーマの基底クラスとして、共通フィールドを提供します。
    データベースモデルとの対応を考慮し、型安全なデータ転送を実現します。

    Attributes:
        id: レコードID（主キー）
        created_at: 作成日時（タイムゾーン対応）
        updated_at: 更新日時（タイムゾーン対応）
    """

    model_config = ConfigDict(
        # SQLAlchemyモデルからの変換を許可
        from_attributes=True,
        # JSON出力時にdatetimeをISO 8601形式で出力
        json_encoders={datetime: lambda v: v.isoformat()},
        # 任意フィールドの型チェックを厳密に
        validate_assignment=True,
        # 不明なフィールドを禁止
        extra="forbid",
    )

    id: Optional[int] = Field(
        default=None,
        description="レコードID（主キー）",
        ge=1,
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="作成日時（タイムゾーン対応）",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="更新日時（タイムゾーン対応）",
    )


class BaseRequestSchema(BaseModel):
    """
    リクエストスキーマ基底クラス

    APIリクエストの雛形を提供します。
    共通フィールド（id, created_at, updated_at）を含みません。

    Note:
        リクエスト時には id, created_at, updated_at はサーバー側で
        自動生成されるため、クライアントから送信する必要はありません。
    """

    model_config = ConfigDict(
        # JSON出力時にdatetimeをISO 8601形式で出力
        json_encoders={datetime: lambda v: v.isoformat()},
        # 任意フィールドの型チェックを厳密に
        validate_assignment=True,
        # 不明なフィールドを禁止
        extra="forbid",
    )


class BaseResponseSchema(BaseSchema):
    """
    レスポンススキーマ基底クラス

    APIレスポンスの雛形を提供します。
    BaseSchemaを継承し、共通フィールド（id, created_at, updated_at）を含みます。

    Note:
        レスポンス時には id, created_at, updated_at は必須フィールドとして
        扱われます。データベースから取得したモデルインスタンスから
        生成することを想定しています。
    """

    # BaseSchemaの設定を継承
    # 必要に応じてレスポンス固有の設定を追加可能


class PaginationRequestSchema(BaseRequestSchema):
    """
    ページネーションリクエストスキーマ

    リスト取得APIのクエリパラメータとして使用します。

    Attributes:
        limit: 取得件数（デフォルト: 100、最大: 1000）
        offset: オフセット（デフォルト: 0）
    """

    limit: int = Field(
        default=100,
        description="取得件数",
        ge=1,
        le=1000,
    )
    offset: int = Field(
        default=0,
        description="オフセット",
        ge=0,
    )


class PaginationResponseSchema(BaseModel):
    """
    ページネーションレスポンススキーマ

    リスト取得APIのレスポンスメタデータとして使用します。

    Attributes:
        total: 総件数
        limit: 取得件数
        offset: オフセット
    """

    model_config = ConfigDict(
        # 任意フィールドの型チェックを厳密に
        validate_assignment=True,
        # 不明なフィールドを禁止
        extra="forbid",
    )

    total: int = Field(
        description="総件数",
        ge=0,
    )
    limit: int = Field(
        description="取得件数",
        ge=1,
        le=1000,
    )
    offset: int = Field(
        description="オフセット",
        ge=0,
    )
