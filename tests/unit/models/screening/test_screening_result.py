"""`ScreeningResult` モデルの単体テスト."""

from datetime import date

from app.models.screening import ScreeningResult


def test_screening_result_fields_and_repr():
    """Model のフィールドが正しく設定され、repr に重要情報が含まれることを確認します."""
    model = ScreeningResult(
        symbol="7203",
        evaluation_year=2026,
        pass_required_conditions=True,
        status="priority",
        total_score=92,
        score_dividend=30,
        score_eps=30,
        score_stability=20,
        score_profitability=12,
        fiscal_year_end=date(2025, 3, 31),
        failed_conditions=["none"],
        screening_details={"notes": "test"},
    )

    assert model.symbol == "7203"
    assert model.status == "priority"
    assert model.total_score == 92
    assert model.score_profitability == 12
    assert model.fiscal_year_end == date(2025, 3, 31)
    assert "priority" in repr(model)
