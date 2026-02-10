"""BaseValidator と ValidationResult の単体テスト."""

from app.services.core.validators.base_validator import BaseValidator, ValidationResult


class ConcreteValidator(BaseValidator):
    """テスト用の具体的な Validator 実装."""

    def validate(self, data: dict) -> ValidationResult:
        """単純な検証ロジックを持つダミー実装です."""
        errors: list[str] = []
        warnings: list[str] = []

        if not self.validate_required_fields(data, ["id", "value"]):
            errors.append("required fields missing")

        if "value" in data and not isinstance(data["value"], str):
            errors.append("value must be string")

        if "id" in data and not self.validate_range(data["id"], min_value=1):
            errors.append("id must be >= 1")

        if data.get("deprecated"):
            warnings.append("field 'deprecated' is deprecated")

        return ValidationResult(len(errors) == 0, errors=errors, warnings=warnings)


class TestValidationResult:
    """`ValidationResult` の基本挙動を検証します."""

    def test_valid_result(self):
        """有効な結果は is_valid が True になることを検証します."""
        r = ValidationResult(True)
        assert r.is_valid

    def test_invalid_result_with_errors(self):
        """エラーありの場合 is_valid が False になることを検証します."""
        r = ValidationResult(False, errors=["x"])
        assert not r.is_valid

    def test_warn_results(self):
        """警告があっても is_valid は True になることを検証します."""
        r = ValidationResult(True, warnings=["w"])
        assert r.is_valid

    def test_repr(self):
        """`__repr__` が識別可能な文字列を返すことを検証します."""
        r = ValidationResult(True)
        assert "ValidationResult" in repr(r)


class TestBaseValidator:
    """`BaseValidator` の基本的な振る舞いを検証します."""

    def test_validate_success(self):
        """正しく実装された Validator が成功することを検証します."""

        class V(BaseValidator):
            def validate(self, data):
                return ValidationResult(True)

        v = V()
        assert v.validate({}).is_valid

    def test_validate_missing_required(self):
        """必須フィールドが欠けている場合に失敗することを検証します."""

        class V(BaseValidator):
            def validate(self, data):
                return ValidationResult(False, errors=["missing"])

        v = V()
        assert not v.validate({}).is_valid

    def test_validate_wrong_type(self):
        """型が不正な場合に失敗することを検証します."""

        class V(BaseValidator):
            def validate(self, data):
                return ValidationResult(False, errors=["type"])

        v = V()
        assert not v.validate({}).is_valid

    def test_validate_out_of_range(self):
        """範囲外の値で失敗することを検証します."""

        class V(BaseValidator):
            def validate(self, data):
                return ValidationResult(False, errors=["range"])

        v = V()
        assert not v.validate({}).is_valid

    def test_validate_with_warnings(self):
        """警告付き検証で is_valid が True になることを検証します."""

        class V(BaseValidator):
            def validate(self, data):
                return ValidationResult(True, warnings=["warn"])

        v = V()
        assert v.validate({}).is_valid

    def test_validate_batch(self):
        """複数回の検証が期待通りに動作することを検証します."""
        v = ConcreteValidator()
        data_list = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
            {"id": 3},
        ]

        results = v.validate_batch(data_list)

        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is True
        assert results[2].is_valid is False

    def test_validate_required_fields(self):
        """必須フィールド検証のテストを実行します."""
        validator = ConcreteValidator()

        assert validator.validate_required_fields({"a": 1, "b": 2}, ["a", "b"]) is True
        assert validator.validate_required_fields({"a": 1}, ["a", "b"]) is False
        assert validator.validate_required_fields({"a": None, "b": 2}, ["a", "b"]) is False

    def test_validate_data_types(self):
        """データ型検証のテストを実行します."""
        validator = ConcreteValidator()

        assert validator.validate_data_types({"a": 1, "b": "test"}, {"a": int, "b": str}) is True
        assert validator.validate_data_types({"a": "1", "b": "test"}, {"a": int, "b": str}) is False
        assert validator.validate_data_types({"a": 1}, {"a": int, "b": str}) is True

    def test_validate_range(self):
        """範囲検証のテストを実行します."""
        validator = ConcreteValidator()

        assert validator.validate_range(5, min_value=1, max_value=10) is True
        assert validator.validate_range(0, min_value=1, max_value=10) is False
        assert validator.validate_range(11, min_value=1, max_value=10) is False
        assert validator.validate_range(1, min_value=1, max_value=10) is True
        assert validator.validate_range(10, min_value=1, max_value=10) is True
        assert validator.validate_range(999) is True
        assert validator.validate_range(-999) is True
