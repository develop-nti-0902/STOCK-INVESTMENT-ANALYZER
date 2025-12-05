"""
BaseConverterの単体テスト
"""

import pytest

from app.services.core.converters.base_converter import BaseConverter


class DummyData:
    """テスト用のPydanticモデル風クラス（pytestがテストクラスと誤認しない名前）"""

    def __init__(self, id_: int, value: str):
        self.id = id_
        self.value = value

    def model_dump(self) -> dict:
        """Pydantic v2のmodel_dump互換"""
        return {"id": self.id, "value": self.value}


class ConcreteConverter(BaseConverter[DummyData]):
    """テスト用の具体的なConverter実装"""

    def to_pydantic(self, data: dict) -> DummyData:
        """辞書からDummyDataへの変換"""
        return DummyData(id_=data["id"], value=data["value"])

    def from_pydantic(self, model: DummyData) -> dict:
        """DummyDataから辞書への変換"""
        return model.model_dump()


class TestBaseConverter:
    """BaseConverterの単体テスト"""

    def test_to_pydantic(self):
        """辞書からモデルへの変換テスト"""
        # Arrange: テスト用のConverterと入力データを準備
        converter = ConcreteConverter()
        data = {"id": 1, "value": "test"}

        # Act: 辞書をモデルに変換
        model = converter.to_pydantic(data)

        # Assert: 変換結果が期待通りであることを検証
        assert isinstance(model, DummyData)
        assert model.id == 1
        assert model.value == "test"

    def test_from_pydantic(self):
        """モデルから辞書への変換テスト"""
        # Arrange: Converterとテスト用モデルを準備
        converter = ConcreteConverter()
        model = DummyData(id_=1, value="test")

        # Act: モデルを辞書に変換
        data = converter.from_pydantic(model)

        # Assert: 変換後の辞書が期待通りであることを検証
        assert isinstance(data, dict)
        assert data["id"] == 1
        assert data["value"] == "test"

    def test_to_pydantic_batch(self):
        """一括変換（辞書→モデル）のテスト"""
        # Arrange: Converterと複数の入力辞書を準備
        converter = ConcreteConverter()
        data_list = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
            {"id": 3, "value": "c"},
        ]

        # Act: 一括変換を実行
        models = converter.to_pydantic_batch(data_list)

        # Assert: すべての要素が変換されていることを検証
        assert len(models) == 3
        assert all(isinstance(m, DummyData) for m in models)
        assert models[0].id == 1
        assert models[1].value == "b"

    def test_from_pydantic_batch(self):
        """一括変換（モデル→辞書）のテスト"""
        # Arrange: Converterと複数のモデルを準備
        converter = ConcreteConverter()
        models = [
            DummyData(id_=1, value="a"),
            DummyData(id_=2, value="b"),
            DummyData(id_=3, value="c"),
        ]

        # Act: 一括変換を実行
        data_list = converter.from_pydantic_batch(models)

        # Assert: 期待通りの辞書リストが返ることを検証
        assert len(data_list) == 3
        assert all(isinstance(d, dict) for d in data_list)
        assert data_list[0]["id"] == 1
        assert data_list[1]["value"] == "b"

    def test_to_dataframe_not_implemented(self):
        """to_dataframeがNotImplementedErrorを発生させることを確認"""
        # Arrange: Converterとダミーモデルリストを準備
        converter = ConcreteConverter()
        models = [DummyData(id_=1, value="a")]

        # Act / Assert: to_dataframeは未実装のためNotImplementedErrorを送出
        with pytest.raises(NotImplementedError):
            converter.to_dataframe(models)

    def test_from_dataframe_not_implemented(self):
        """from_dataframeがNotImplementedErrorを発生させることを確認"""
        # Arrange: Converterを準備
        converter = ConcreteConverter()

        # Act / Assert: from_dataframeは未実装のためNotImplementedErrorを送出
        with pytest.raises(NotImplementedError):
            converter.from_dataframe(None)
