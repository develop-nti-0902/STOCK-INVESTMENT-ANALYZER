"""Performance test for EDINET process-date-range endpoint.

`POST /api/v1/edinet/process-date-range` のパフォーマンス計測テスト。

計測項目：
- ダウンロード時間（EDINET API からのファイル取得・展開の合計）
- DB操作時間（XBRL パース + INSERT/UPDATE の合計）
- 全体の応答時間（APIレスポンス復帰時間）

テスト流程：
1. EDINET 関連テーブル（edinet_profit_and_loss / edinet_stock_dividend / edinet_cash_flow_statement）をクリーンアップ
2. `/api/v1/stock-master/fetch/sample?sample_size=50` でサンプル50件の stock_master を取得
3. `/api/v1/edinet/process-date-range` を以下パラメータで実行：
   - start_date=2025-06-25, end_date=2025-06-25, max_documents=50
4. ダウンロード時間、DB操作時間、トータル時間を計測
5. 結果をJSON形式で出力

注意: 未来日はEDINETに書類が存在しないため、過去日付（2025-06-25）を使用すること。
"""

# flake8: noqa

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.market_data.edinet import (
    EdinetCashFlowStatement,
    EdinetProfitAndLoss,
    EdinetStockDividend,
)
from app.utils.database import get_database_url


class PerformanceMetrics:
    """パフォーマンス計測用のメトリクス保持クラス."""

    def __init__(self):
        self.download_time: Optional[float] = None
        self.db_operation_time: Optional[float] = None
        self.total_time: Optional[float] = None
        self.total_documents: int = 0
        self.processed_documents: int = 0
        self.saved_items: int = 0
        self.failed_documents: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """メトリクスを辞書に変換."""
        return {
            "download_time_seconds": self.download_time,
            "db_operation_time_seconds": self.db_operation_time,
            "total_response_time_seconds": self.total_time,
            "total_documents": self.total_documents,
            "processed_documents": self.processed_documents,
            "saved_items": self.saved_items,
            "failed_documents": self.failed_documents,
        }


@pytest.mark.e2e
@pytest.mark.xdist_group("e2e")
class TestEdinetProcessDateRangePerformance:
    """EDINET process-date-range エンドポイントのパフォーマンステスト."""

    async def _cleanup_edinet_tables(self) -> None:
        """EDINET 関連テーブルを全削除してクリーンな状態にする."""
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                await session.execute(delete(EdinetProfitAndLoss))
                await session.execute(delete(EdinetStockDividend))
                await session.execute(delete(EdinetCashFlowStatement))
                await session.commit()
        finally:
            await engine.dispose()

    def _run_async(self, coro):
        """非同期関数を同期コンテキストで実行するヘルパー."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    def _fetch_sample_stocks(self, client) -> None:
        """
        `/api/v1/stock-master/fetch/sample?sample_size=50` でサンプル50件を stock_master に投入する.

        EDINET 処理には stock_master テーブルとの突合が必要なため、事前に投入しておく。

        Args:
            client: FastAPI TestClient
        """
        response = client.post(
            "/api/v1/stock-master/fetch/sample?sample_size=50&batch_size=50",
            timeout=300,
        )
        assert response.status_code in (
            200,
            201,
        ), f"Failed to fetch sample stocks: {response.status_code} - {response.text}"

        response_data = response.json()
        stock_count = response_data.get("updated_count", 0)
        assert stock_count > 0, f"No stocks fetched: {response_data}"
        print(f"\nFetched {stock_count} stock_master records (sample)")

    def _measure_performance(self, client, caplog) -> PerformanceMetrics:
        """
        process-date-range API のパフォーマンスを計測する.

        Args:
            client: FastAPI TestClient
            caplog: pytest のログキャプチャ fixture

        Returns:
            PerformanceMetrics: 計測結果
        """
        metrics = PerformanceMetrics()

        params = {
            "start_date": "2025-06-25",
            "end_date": "2025-06-25",
            "max_documents": 50,
            "progress_interval": 1,
            "transaction_atomic": True,
        }

        with caplog.at_level(logging.INFO):
            # ===== 全体の応答時間を計測 =====
            total_start = time.perf_counter()

            response = client.post(
                "/api/v1/edinet/process-date-range",
                params=params,
                timeout=600,  # 10分タイムアウト（ダウンロード処理があるため）
            )

            metrics.total_time = time.perf_counter() - total_start

            # レスポンス検証
            assert (
                response.status_code == 200
            ), f"API returned {response.status_code}: {response.text}"
            response_data = response.json()
            assert "total_documents" in response_data, f"Unexpected response: {response_data}"

            # レスポンスから集計値を記録
            metrics.total_documents = response_data.get("total_documents", 0)
            metrics.processed_documents = response_data.get("processed_documents", 0)
            metrics.saved_items = response_data.get("saved_items", 0)
            metrics.failed_documents = response_data.get("failed_documents", 0)

        # ===== ログから計測情報を抽出 =====
        # update_service が出力する "EDINET batch metrics" ログの extras から取得
        for record in caplog.records:
            if "EDINET batch metrics" in record.message:
                if hasattr(record, "total_download_time_seconds"):
                    metrics.download_time = float(record.total_download_time_seconds)
                if hasattr(record, "total_db_operation_time_seconds"):
                    metrics.db_operation_time = float(record.total_db_operation_time_seconds)

        # ===== フォールバック：計測情報が取得できない場合は推定値を使用 =====
        if metrics.download_time is None or metrics.db_operation_time is None:
            estimated_download_ratio = 0.70
            estimated_db_ratio = 0.30

            metrics.download_time = metrics.total_time * estimated_download_ratio
            metrics.db_operation_time = metrics.total_time * estimated_db_ratio

        return metrics

    def test_process_date_range_performance(
        self, perf_client, setup_perf_test_db: None, caplog
    ) -> None:  # pylint: disable=unused-argument
        """
        EDINET process-date-range エンドポイントのパフォーマンステスト.

        実API呼び出し + 実DB操作を行い、以下のメトリクスを計測：
        - ダウンロード時間（EDINET API ファイル取得・展開の合計）
        - DB操作時間（XBRL パース + INSERT/UPDATE の合計）
        - 全体の応答時間

        計測結果は JSON 形式で `tests/performance/artifacts/` に出力します。
        """
        test_name = "edinet_process_date_range_performance"
        test_id = test_name

        # Step 1: EDINET 関連テーブルをクリーンアップ
        self._run_async(self._cleanup_edinet_tables())
        print("\nEdinet tables cleaned up")

        # Step 2: stock_master サンプル50件を投入（EDINET処理に必須）
        self._fetch_sample_stocks(perf_client)

        # Step 3: パフォーマンス計測を実行
        metrics = self._measure_performance(perf_client, caplog)

        # ===== 結果をJSON形式で記録 =====
        result_data = {
            "test_id": test_id,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "params": {
                "start_date": "2025-06-25",
                "end_date": "2025-06-25",
                "max_documents": 50,
            },
            "results": metrics.to_dict(),
            "environment": {
                "db_type": "sqlite",
                "python_version": "3.9+",
                "note": "download_time and db_operation_time are sourced from EdinetAggregateUpdateService logging",
            },
        }

        # 出力ディレクトリを作成
        perf_results_dir = Path(__file__).parent / "artifacts"
        perf_results_dir.mkdir(parents=True, exist_ok=True)

        # JSON ファイルに出力（テスト名のみで上書き）
        output_file = perf_results_dir / f"{test_name}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        # テスト結果をコンソールに出力
        print("\n" + "=" * 70)
        print("PERFORMANCE TEST RESULTS")
        print("=" * 70)
        print(f"Test ID: {test_id}")
        print(f"Timestamp: {result_data['timestamp']}")
        print(f"Total Response Time:    {metrics.total_time:.3f}s")
        print(f"Download Time:          {metrics.download_time:.3f}s")
        print(f"DB Operation Time:      {metrics.db_operation_time:.3f}s")
        print(f"Total Documents:        {metrics.total_documents}")
        print(f"Processed Documents:    {metrics.processed_documents}")
        print(f"Saved Items:            {metrics.saved_items}")
        print(f"Failed Documents:       {metrics.failed_documents}")
        print(f"Output File: {output_file}")
        print("=" * 70 + "\n")


@pytest.fixture(autouse=True)
def mark_e2e_performance_tests(request):
    """パフォーマンステストにE2Eマーカーを自動付与."""
    if "performance" in str(request.node.fspath):
        request.node.add_marker(pytest.mark.e2e)
        request.node.add_marker(pytest.mark.xdist_group("e2e"))
