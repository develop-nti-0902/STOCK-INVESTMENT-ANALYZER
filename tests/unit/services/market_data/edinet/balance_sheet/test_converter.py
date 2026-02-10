"""`EdinetBalanceSheetConverter` の単体テスト.

テスト規約に従い、短く独立したケースで正規化・変換ロジックを検証します。
"""

from decimal import Decimal

import pytest

from app.services.market_data.edinet.balance_sheet.converter import EdinetBalanceSheetConverter


def test_to_pydantic_success():
    """正常系: データが正しく Pydantic モデルへ変換されることを検証する."""
    conv = EdinetBalanceSheetConverter()

    data = {
        "doc_id": "D001",
        "sec_code": "7203",
        "filer_name": "  Example Corp  ",
        "submission_date": "2023-05-10",
        "period_end": "2022-03-31",
        "assets": "1000",
        "liabilities": 400,
        "equity": 600,
        "consolidation": True,
    }

    model = conv.to_pydantic(data)

    assert model.doc_id == "D001"
    assert model.sec_code == "7203"
    # filer_name should be preserved (stripped later by schema validators)
    assert "Example" in model.filer_name
    assert model.fiscal_year == 2022
    assert isinstance(model.total_assets, Decimal)
    assert model.total_assets == Decimal("1000")
    assert model.total_liabilities == Decimal("400")
    assert model.total_equity == Decimal("600")
    assert model.is_consolidated is True


def test_to_pydantic_missing_period_end_raises():
    """period_end が欠落した場合に ValueError が送出されることを検証する."""
    conv = EdinetBalanceSheetConverter()

    data = {"doc_id": "D002", "sec_code": "0000", "period_end": None}

    with pytest.raises(ValueError):
        conv.to_pydantic(data)


def test_to_pydantic_invalid_period_end_raises_validation_error():
    """無効な period_end フォーマットでバリデーションエラーが発生することを検証する."""
    conv = EdinetBalanceSheetConverter()

    data = {
        "doc_id": "D003",
        "sec_code": "1111",
        "submission_date": "2020-01-01",
        "period_end": "not-a-date",
        "assets": "not-a-number",
        "liabilities": None,
        "equity": "123.45",
        "consolidation": False,
    }

    # period_end is present but invalid format -> Pydantic raises ValidationError
    with pytest.raises(Exception):
        conv.to_pydantic(data)


def test_to_pydantic_handles_bad_numbers_with_valid_date():
    """数値フィールドが不正でも変換できるフィールドは処理されることを検証する."""
    conv = EdinetBalanceSheetConverter()

    data = {
        "doc_id": "D005",
        "sec_code": "2222",
        "submission_date": "2020-01-01",
        "period_end": "2020-12-31",
        "assets": "not-a-number",
        "liabilities": None,
        "equity": "123.45",
        "consolidation": False,
    }

    model = conv.to_pydantic(data)

    # assets could not be converted -> None
    assert model.total_assets is None
    # liabilities None -> None
    assert model.total_liabilities is None
    # equity convertible
    assert model.total_equity == Decimal("123.45")


def test_to_saver_records_and_from_pydantic_roundtrip():
    """Pydantic から Saver 用辞書への変換が正しく行われることを検証する."""
    conv = EdinetBalanceSheetConverter()

    data = {
        "doc_id": "D004",
        "sec_code": "9999",
        "submission_date": "2021-06-30",
        "period_end": "2020-12-31",
        "assets": 2000,
        "liabilities": 1200,
        "equity": 800,
        "consolidation": None,
    }

    model = conv.to_pydantic(data)
    records = conv.to_saver_records([model])

    assert isinstance(records, list)
    assert len(records) == 1

    rec = records[0]
    # from_pydantic is alias of _to_saver_record -> keys present
    assert rec["doc_id"] == model.doc_id
    assert rec["sec_code"] == model.sec_code
    assert rec["total_assets"] == model.total_assets

    # from_pydantic should return same as _to_saver_record
    rec2 = conv.from_pydantic(model)
    assert rec2 == rec


def test_from_dataframe_not_implemented():
    """from_dataframe は未実装で NotImplementedError を投げることを検証する."""
    conv = EdinetBalanceSheetConverter()

    with pytest.raises(NotImplementedError):
        conv.from_dataframe(None)
