"""
スキーマ層 - 基底クラスの単体テスト

BaseSchema, BaseRequestSchema, BaseResponseSchemaの単体テストを実装する。
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.base import (
    BaseRequestSchema,
    BaseResponseSchema,
    BaseSchema,
    PaginationRequestSchema,
    PaginationResponseSchema,
)


class TestBaseSchema:
    """BaseSchemaのテストクラス"""

    def test_base_schema_with_all_fields(self):
        """全フィールドを指定した場合のテスト"""
        # Arrange
        now = datetime.now(timezone.utc)

        # Act
        schema = BaseSchema(
            id=1,
            created_at=now,
            updated_at=now,
        )

        # Assert
        assert schema.id == 1
        assert schema.created_at == now
        assert schema.updated_at == now

    def test_base_schema_with_optional_fields(self):
        """オプショナルフィールドを省略した場合のテスト"""
        # Arrange / Act
        schema = BaseSchema()

        # Assert
        assert schema.id is None
        assert schema.created_at is None
        assert schema.updated_at is None

    def test_base_schema_id_validation_negative(self):
        """idの範囲検証（負の値）"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseSchema(id=-1)

        # Assert (検証エラーの内容)
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "greater_than_equal"
        assert errors[0]["loc"] == ("id",)

    def test_base_schema_id_validation_zero(self):
        """idの範囲検証（0）"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseSchema(id=0)

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "greater_than_equal"
        assert errors[0]["loc"] == ("id",)

    def test_base_schema_id_validation_positive(self):
        """idの範囲検証（正の値）"""
        # Arrange / Act
        schema = BaseSchema(id=1)

        # Assert
        assert schema.id == 1

    def test_base_schema_extra_field_forbidden(self):
        """不明なフィールドが禁止されていることのテスト"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseSchema(id=1, unknown_field="test")

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert errors[0]["loc"] == ("unknown_field",)

    def test_base_schema_datetime_iso_format(self):
        """datetime型のISO 8601形式出力テスト"""
        # Arrange
        now = datetime(2025, 12, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Act
        schema = BaseSchema(
            id=1,
            created_at=now,
            updated_at=now,
        )
        json_str = schema.model_dump_json()

        # Assert
        assert "2025-12-01T12:00:00+00:00" in json_str

    def test_base_schema_from_attributes(self):
        """SQLAlchemyモデルからの変換テスト（モック）"""

        class MockModel:
            """SQLAlchemyモデルのモック"""

            def __init__(self):
                self.id = 1
                self.created_at = datetime(
                    2025, 12, 1, 12, 0, 0, tzinfo=timezone.utc
                )
                self.updated_at = datetime(
                    2025, 12, 1, 12, 0, 0, tzinfo=timezone.utc
                )

        # Arrange
        mock_model = MockModel()

        # Act
        schema = BaseSchema.model_validate(mock_model)

        # Assert
        assert schema.id == 1
        assert schema.created_at == mock_model.created_at
        assert schema.updated_at == mock_model.updated_at


class TestBaseRequestSchema:
    """BaseRequestSchemaのテストクラス"""

    def test_base_request_schema_empty(self):
        """空のリクエストスキーマのテスト"""
        # Arrange / Act
        schema = BaseRequestSchema()

        # Assert
        assert schema is not None

    def test_base_request_schema_extra_field_forbidden(self):
        """不明なフィールドが禁止されていることのテスト"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseRequestSchema(unknown_field="test")

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert errors[0]["loc"] == ("unknown_field",)


class TestBaseResponseSchema:
    """BaseResponseSchemaのテストクラス"""

    def test_base_response_schema_with_all_fields(self):
        """全フィールドを指定した場合のテスト"""
        # Arrange
        now = datetime.now(timezone.utc)

        # Act
        schema = BaseResponseSchema(
            id=1,
            created_at=now,
            updated_at=now,
        )

        # Assert
        assert schema.id == 1
        assert schema.created_at == now
        assert schema.updated_at == now

    def test_base_response_schema_inherits_base_schema(self):
        """BaseSchemaを継承していることのテスト"""
        # Arrange / Act & Assert
        assert issubclass(BaseResponseSchema, BaseSchema)


class TestPaginationRequestSchema:
    """PaginationRequestSchemaのテストクラス"""

    def test_pagination_request_schema_default_values(self):
        """デフォルト値のテスト"""
        # Arrange / Act
        schema = PaginationRequestSchema()

        # Assert
        assert schema.limit == 100
        assert schema.offset == 0

    def test_pagination_request_schema_custom_values(self):
        """カスタム値のテスト"""
        # Arrange / Act
        schema = PaginationRequestSchema(limit=50, offset=10)

        # Assert
        assert schema.limit == 50
        assert schema.offset == 10

    def test_pagination_request_schema_limit_validation_min(self):
        """limitの最小値検証"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PaginationRequestSchema(limit=0)

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "greater_than_equal"
        assert errors[0]["loc"] == ("limit",)

    def test_pagination_request_schema_limit_validation_max(self):
        """limitの最大値検証"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PaginationRequestSchema(limit=1001)

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "less_than_equal"
        assert errors[0]["loc"] == ("limit",)

    def test_pagination_request_schema_offset_validation_negative(self):
        """offsetの範囲検証（負の値）"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PaginationRequestSchema(offset=-1)

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "greater_than_equal"
        assert errors[0]["loc"] == ("offset",)


class TestPaginationResponseSchema:
    """PaginationResponseSchemaのテストクラス"""

    def test_pagination_response_schema_with_all_fields(self):
        """全フィールドを指定した場合のテスト"""
        # Arrange / Act
        schema = PaginationResponseSchema(
            total=100,
            limit=50,
            offset=10,
        )

        # Assert
        assert schema.total == 100
        assert schema.limit == 50
        assert schema.offset == 10

    def test_pagination_response_schema_total_validation_negative(self):
        """totalの範囲検証（負の値）"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PaginationResponseSchema(total=-1, limit=100, offset=0)

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "greater_than_equal"
        assert errors[0]["loc"] == ("total",)

    def test_pagination_response_schema_total_validation_zero(self):
        """totalの範囲検証（0）"""
        # Arrange / Act
        schema = PaginationResponseSchema(total=0, limit=100, offset=0)

        # Assert
        assert schema.total == 0

    def test_pagination_response_schema_limit_validation_min(self):
        """limitの最小値検証"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PaginationResponseSchema(total=100, limit=0, offset=0)

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "greater_than_equal"
        assert errors[0]["loc"] == ("limit",)

    def test_pagination_response_schema_limit_validation_max(self):
        """limitの最大値検証"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PaginationResponseSchema(total=100, limit=1001, offset=0)

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "less_than_equal"
        assert errors[0]["loc"] == ("limit",)

    def test_pagination_response_schema_offset_validation_negative(self):
        """offsetの範囲検証（負の値）"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PaginationResponseSchema(total=100, limit=100, offset=-1)

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "greater_than_equal"
        assert errors[0]["loc"] == ("offset",)

    def test_pagination_response_schema_extra_field_forbidden(self):
        """不明なフィールドが禁止されていることのテスト"""
        # Arrange / Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PaginationResponseSchema(
                total=100, limit=100, offset=0, unknown_field="test"
            )

        # Assert
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert errors[0]["loc"] == ("unknown_field",)
