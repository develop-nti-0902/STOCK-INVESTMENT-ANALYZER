"""Performance test for screening run endpoint.

`POST /api/v1/screening/run` エンドポイントのパフォーマンス計測テスト。

計測項目：
- DB操作時間（スクリーニング実行・結果取得）
- 全体の応答時間（APIレスポンス復帰時間）
- screening_results テーブル更新確認

テスト流程：
1. `loaded_edinet_test_data` fixture でテストデータを投入
2. screening_results テーブルをクリア
3. `POST /api/v1/screening/run?evaluation_date=2025-03-31` を実行
4. 全体の応答時間を計測
5. screening_results テーブルにデータが挿入されたことを確認
6. 結果をJSON形式で出力
"""

# flake8: noqa

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.screening.screening_result import ScreeningResult
from app.utils.database import get_database_url


class PerformanceMetrics:
    """パフォーマンス計測用のメトリクス保持クラス."""

    def __init__(self):
        self.total_time: Optional[float] = None
        self.db_operation_time: Optional[float] = None
        self.evaluation_date: str = ""
        self.result_count: int = 0
        self.db_records_inserted: int = 0
        self.db_verification_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """メトリクスを辞書に変換."""
        return {
            "total_response_time_seconds": self.total_time,
            "db_operation_time_seconds": self.db_operation_time,
            "result_count": self.result_count,
            "evaluation_date": self.evaluation_date,
            "db_records_inserted": self.db_records_inserted,
            "db_verification_passed": self.db_verification_passed,
        }


@pytest.mark.e2e
@pytest.mark.xdist_group("e2e")
class TestScreeningRunPerformance:
    """Screening Run エンドポイントのパフォーマンステスト."""

    def _run_async_task(self, coro):
        """非同期タスクを同期コンテキストで実行するヘルパー."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    async def _clear_screening_results_table(self) -> None:
        """screening_results テーブルをクリア."""
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                await session.execute(delete(ScreeningResult))
                await session.commit()
        finally:
            await engine.dispose()

    async def _count_screening_results(self) -> int:
        """screening_results テーブルのレコード数を取得."""
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(ScreeningResult))
                rows = result.scalars().all()
                return len(rows)
        finally:
            await engine.dispose()

    def _measure_screening_performance(
        self, client: TestClient, evaluation_date: str, caplog
    ) -> PerformanceMetrics:
        """
        スクリーニング実行のパフォーマンスを計測.

        Args:
            client: FastAPI TestClient
            evaluation_date: 評価実行日（ISO形式）
            caplog: pytest のログキャプチャ fixture

        Returns:
            PerformanceMetrics: 計測結果
        """
        metrics = PerformanceMetrics()
        metrics.evaluation_date = evaluation_date

        # ===== screening_results テーブルをクリア =====
        self._run_async_task(self._clear_screening_results_table())

        # ロギングレベルを INFO に設定して計測情報をキャプチャ
        with caplog.at_level(logging.INFO):
            # ===== 全体の応答時間を計測 =====
            total_start = time.perf_counter()

            # スクリーニング実行エンドポイントを呼び出し
            response = client.post(
                f"/api/v1/screening/run?evaluation_date={evaluation_date}",
            )

            total_end = time.perf_counter()
            metrics.total_time = total_end - total_start

            # レスポンス検証
            assert (
                response.status_code == 200
            ), f"API returned {response.status_code}: {response.text}"
            response_data = response.json()
            assert response_data.get("status") == "success", f"Unexpected response: {response_data}"

            # 結果件数を取得
            result_list = response_data.get("result", [])
            metrics.result_count = len(result_list)

        # ===== ログから計測情報を抽出 =====
        # Service層が出力する計測情報をログレコードから取得
        db_time = None

        for record in caplog.records:
            if "screening" in record.message.lower() or "evaluation" in record.message.lower():
                # ログからDB操作時間を抽出（あれば）
                if hasattr(record, "db_time_seconds"):
                    db_time = float(record.db_time_seconds)

        # ===== フォールバック：計測情報が取得できない場合は推定値を使用 =====
        if db_time is None:
            # ヒューリスティック推定：全体の約70%がDB操作（API + DB操作）
            estimated_db_ratio = 0.70
            db_time = metrics.total_time * estimated_db_ratio

        metrics.db_operation_time = db_time

        # ===== screening_results テーブルの更新確認 =====
        db_record_count = self._run_async_task(self._count_screening_results())
        metrics.db_records_inserted = db_record_count
        metrics.db_verification_passed = db_record_count > 0

        return metrics

    def test_screening_run_performance(
        self, client: TestClient, loaded_edinet_test_data: Dict, caplog
    ) -> None:
        """
        Screening Run エンドポイントのパフォーマンステスト.

        実API呼び出し + 実DB操作を行い、以下のメトリクスを計測：
        - DB操作時間（スクリーニング実行・結果取得）
        - 全体の応答時間（APIレスポンス復帰時間）
        - screening_results テーブルのデータ挿入確認

        計測結果は JSON 形式で `tests/performance/artifacts/` に出力します。

        Args:
            client: FastAPI TestClient
            loaded_edinet_test_data: EDINET テストデータ（fixture）
            caplog: pytest ログキャプチャ fixture
        """
        # テスト名（ファイル名に使用、実行ごとに上書き）
        test_name = "screening_run_performance"
        test_id = test_name
        evaluation_date = "2025-03-31"

        # 計測を実行
        metrics = self._measure_screening_performance(client, evaluation_date, caplog)

        # ===== DB検証アサーション =====
        assert (
            metrics.db_verification_passed
        ), f"screening_results テーブルにデータが挿入されていません (count: {metrics.db_records_inserted})"

        # ===== 結果をJSON形式で記録 =====
        result_data = {
            "test_id": test_id,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "results": metrics.to_dict(),
            "environment": {
                "db_type": "sqlite",
                "python_version": "3.9+",
                "note": "db_operation_time is estimated from total response time; actual time may vary",
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
        print(f"Total Response Time: {metrics.total_time:.3f}s")
        print(f"DB Operation Time (estimated): {metrics.db_operation_time:.3f}s")
        print(f"Result Count: {metrics.result_count}")
        print(f"Evaluation Date: {metrics.evaluation_date}")
        print(f"DB Records Inserted: {metrics.db_records_inserted}")
        print(f"DB Verification: {'✅ PASSED' if metrics.db_verification_passed else '❌ FAILED'}")
        print(f"Output File: {output_file}")
        print("=" * 70 + "\n")


@pytest.fixture(autouse=True)
def mark_e2e_performance_tests(request):
    """パフォーマンステストにE2Eマーカーを自動付与."""
    if "performance" in str(request.node.fspath):
        request.node.add_marker(pytest.mark.e2e)
        request.node.add_marker(pytest.mark.xdist_group("e2e"))
