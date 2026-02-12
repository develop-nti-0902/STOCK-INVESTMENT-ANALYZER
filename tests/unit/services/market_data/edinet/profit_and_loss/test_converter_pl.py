"""EdinetProfitAndLoss の Converter の単体テスト（profit_and_loss 固有）。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas.edinet_profit_and_loss import EdinetProfitAndLossCreate
from app.services.market_data.edinet.profit_and_loss.converter import EdinetProfitAndLossConverter


def test_to_pydantic_success():
    data = {
        "doc_id": "DUMMY_DOC",
        "sec_code": "7203",
        "filer_name": "  Test Co.  ",
        "submission_date": "2025-02-01",
        "period_end_date": "2024-03-31",
        "operating_profit": "1234.5",
        "eps": 120.5,
    }

    conv = EdinetProfitAndLossConverter()
    model = conv.to_pydantic(data)

    assert isinstance(model, EdinetProfitAndLossCreate)
    assert model.filer_name == "Test Co."
    assert model.fiscal_year == 2024
    assert isinstance(model.operating_profit, Decimal)


def test_to_pydantic_missing_period_end_date_raises():
    data = {"doc_id": "D1", "sec_code": "X", "submission_date": "2025-01-01"}
    conv = EdinetProfitAndLossConverter()
    with pytest.raises(ValueError):
        conv.to_pydantic(data)


def test_decimal_conversion_invalid_values_produce_none():
    data = {
        "doc_id": "D2",
        "sec_code": "0001",
        "submission_date": "2025-01-01",
        "period_end_date": "2024-12-31",
        "operating_profit": "not_a_number",
        "eps": None,
    }
    conv = EdinetProfitAndLossConverter()
    model = conv.to_pydantic(data)

    assert model.operating_profit is None
    assert model.eps is None


def test_from_dataframe_not_implemented():
    conv = EdinetProfitAndLossConverter()
    with pytest.raises(NotImplementedError):
        conv.from_dataframe(None)
