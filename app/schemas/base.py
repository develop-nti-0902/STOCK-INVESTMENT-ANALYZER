"""スキーマ層 - 基底クラス.

全ての Pydantic スキーマの基底クラス群を定義します。共通フィールド
(`id`, `created_at`, `updated_at`) やリクエスト／レスポンスの雛形を提供します。

仕様書: docs/architecture/layers/service_layer.md 7章、data_access_layer.md 3.1章
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class BaseSchema(BaseModel):
    """スキーマ基底クラス（共通フィールド）.

    Attributes:
        id (Optional[int]): レコードID（主キー）
        created_at (Optional[datetime]): 作成日時（タイムゾーン対応）
        updated_at (Optional[datetime]): 更新日時（タイムゾーン対応）
    """

    model_config = ConfigDict(
        # SQLAlchemyモデルからの変換を許可
        from_attributes=True,
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

    @field_serializer("created_at", "updated_at")
    def _serialize_datetimes(self, v: datetime | None, _info) -> str | None:
        """datetime を ISO-8601 形式にシリアライズする.

        Args:
            v (Optional[datetime]): シリアライズする日時
            _info: シリアライザ情報（内部利用）

        Returns:
            Optional[str]: ISO-8601 形式の文字列、または None
        """
        if v is None:
            return None
        return v.isoformat()


class BaseRequestSchema(BaseModel):
    """リクエストスキーマ基底クラス.

    Note:
        リクエスト時には `id`, `created_at`, `updated_at` はサーバー側で
        自動生成されるため、クライアントから送信する必要はありません。
    """

    model_config = ConfigDict(
        # 任意フィールドの型チェックを厳密に
        validate_assignment=True,
        # 不明なフィールドを禁止
        extra="forbid",
    )


class BaseResponseSchema(BaseSchema):
    """レスポンススキーマ基底クラス.

    BaseSchema を継承し、レスポンス用の共通フィールドを提供します。

    Note:
        レスポンス時には `id`, `created_at`, `updated_at` を含むことを想定しています。
    """

    # BaseSchemaの設定を継承
    # 必要に応じてレスポンス固有の設定を追加可能


class PaginationRequestSchema(BaseRequestSchema):
    """ページネーションリクエストスキーマ.

    Attributes:
        limit (int): 取得件数（デフォルト: 100、最大: 1000）
        offset (int): オフセット（デフォルト: 0）
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
    """ページネーションレスポンススキーマ.

    Attributes:
        total (int): 総件数
        limit (int): 取得件数
        offset (int): オフセット
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
