"""
BaseValidatorとValidationResultの単体テスト
"""

from app.services.core.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class ConcreteValidator(BaseValidator):
    """テスト用の具体的なValidator実装"""

    def validate(self, data: dict) -> ValidationResult:
        """テスト用のvalidate実装"""
        errors = []
        warnings = []

        # 必須フィールドチェック
        if not self.validate_required_fields(data, ["id", "value"]):
            errors.append("Required fields missing")

        # データ型チェック
        if "value" in data and not isinstance(data["value"], str):
            errors.append("Value must be string")

        # 範囲チェック
        if "id" in data and not self.validate_range(data["id"], min_value=1):
            errors.append("ID must be >= 1")

        # 警告チェック
        if data.get("deprecated"):
            warnings.append("Field 'deprecated' is deprecated")

        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings)


class TestValidationResult:
    """ValidationResultの単体テスト"""

    def test_valid_result(self):
        """有効な結果のテスト"""
        result = ValidationResult(True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert bool(result) is True

    def test_invalid_result_with_errors(self):
        """エラーありの無効な結果のテスト"""
        result = ValidationResult(False, errors=["Error 1", "Error 2"])
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.errors[0] == "Error 1"
        assert bool(result) is False

    def test_valid_result_with_warnings(self):
        """警告ありの有効な結果のテスト"""
        result = ValidationResult(True, warnings=["Warning 1"])
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Warning 1"
        assert bool(result) is True

    def test_repr(self):
        """__repr__のテスト"""
        result = ValidationResult(
            False, errors=["Error"], warnings=["Warning"]
        )
        repr_str = repr(result)
        assert "ValidationResult" in repr_str
        assert "is_valid=False" in repr_str


class TestBaseValidator:
    """BaseValidatorの単体テスト"""

    def test_validate_success(self):
        """正常な検証のテスト"""
        validator = ConcreteValidator()
        data = {"id": 1, "value": "test"}
        result = validator.validate(data)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_missing_fields(self):
        """必須フィールド欠如のテスト"""
        validator = ConcreteValidator()
        data = {"id": 1}
        result = validator.validate(data)
        assert result.is_valid is False
        assert "Required fields missing" in result.errors

    def test_validate_invalid_type(self):
        """データ型不正のテスト"""
        validator = ConcreteValidator()
        data = {"id": 1, "value": 123}  # valueはstr型であるべき
        result = validator.validate(data)
        assert result.is_valid is False
        assert "Value must be string" in result.errors

    def test_validate_invalid_range(self):
        """範囲外の値のテスト"""
        validator = ConcreteValidator()
        data = {"id": 0, "value": "test"}  # idは1以上であるべき
        result = validator.validate(data)
        assert result.is_valid is False
        assert "ID must be >= 1" in result.errors

    def test_validate_with_warnings(self):
        """警告付き検証のテスト"""
        validator = ConcreteValidator()
        data = {"id": 1, "value": "test", "deprecated": True}
        result = validator.validate(data)
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "deprecated" in result.warnings[0]

    def test_validate_batch(self):
        """一括検証のテスト"""
        validator = ConcreteValidator()
        data_list = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
            {"id": 3},  # 無効
        ]
        results = validator.validate_batch(data_list)
        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is True
        assert results[2].is_valid is False

    def test_validate_required_fields(self):
        """必須フィールド検証のテスト"""
        validator = ConcreteValidator()

        # 全て存在
        assert (
            validator.validate_required_fields({"a": 1, "b": 2}, ["a", "b"])
            is True
        )
        # 一部欠如
        assert (
            validator.validate_required_fields({"a": 1}, ["a", "b"]) is False
        )
        # Noneは無効
        assert (
            validator.validate_required_fields({"a": None, "b": 2}, ["a", "b"])
            is False
        )

    def test_validate_data_types(self):
        """データ型検証のテスト"""
        validator = ConcreteValidator()

        # 正しい型
        assert (
            validator.validate_data_types(
                {"a": 1, "b": "test"}, {"a": int, "b": str}
            )
            is True
        )
        # 型不一致
        assert (
            validator.validate_data_types(
                {"a": "1", "b": "test"}, {"a": int, "b": str}
            )
            is False
        )
        # 存在しないフィールドはスキップ
        assert (
            validator.validate_data_types({"a": 1}, {"a": int, "b": str})
            is True
        )

    def test_validate_range(self):
        """範囲検証のテスト"""
        validator = ConcreteValidator()

        # 範囲内
        assert validator.validate_range(5, min_value=1, max_value=10) is True
        # 下限未満
        assert validator.validate_range(0, min_value=1, max_value=10) is False
        # 上限超過
        assert validator.validate_range(11, min_value=1, max_value=10) is False
        # 境界値
        assert validator.validate_range(1, min_value=1, max_value=10) is True
        assert validator.validate_range(10, min_value=1, max_value=10) is True
        # 無制限
        assert validator.validate_range(999) is True
        assert validator.validate_range(-999) is True
