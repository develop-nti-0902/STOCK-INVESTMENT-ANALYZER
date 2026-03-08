"""配当利回り履歴スキーマ単体テスト。"""

from datetime import date

from app.schemas.dividend_yield_history import (
    GenerateDividendYieldHistoryRequest,
    GenerateDividendYieldHistoryResponse,
)


class TestGenerateDividendYieldHistoryRequest:
    """GenerateDividendYieldHistoryRequest のテスト."""

    def test_valid_request(self):
        """有効なリクエスト作成テスト."""
        # Arrange
        target_date = date(2024, 1, 1)

        # Act
        request = GenerateDividendYieldHistoryRequest(target_date=target_date)

        # Assert
        assert request.target_date == target_date


class TestGenerateDividendYieldHistoryResponse:
    """GenerateDividendYieldHistoryResponse のテスト."""

    def test_valid_response(self):
        """有効なレスポンス作成テスト."""
        # Arrange
        status = "completed"
        rowcount = 100
        skipped_count = 5
        error_count = 0
        message = "Successfully generated"

        # Act
        response = GenerateDividendYieldHistoryResponse(
            status=status,
            rowcount=rowcount,
            skipped_count=skipped_count,
            error_count=error_count,
            message=message,
        )

        # Assert
        assert response.status == status
        assert response.rowcount == rowcount
        assert response.skipped_count == skipped_count
        assert response.error_count == error_count
        assert response.message == message

    def test_response_with_none_message(self):
        """message が None のレスポンステスト."""
        # Act
        response = GenerateDividendYieldHistoryResponse(
            status="completed",
            rowcount=100,
            skipped_count=5,
            error_count=0,
        )

        # Assert
        assert response.message is None
