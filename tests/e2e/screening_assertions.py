"""Assertion helpers for screening result validation."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class ScreeningAssertions:
    """Validate screening results using assertion methods."""

    @staticmethod
    def assert_response_schema(response: dict) -> None:
        """
        Validate API response schema.

        Args:
            response: API レスポンスオブジェクト

        Raises:
            AssertionError: スキーマ検証失敗時
        """
        assert "screening_results" in response, "screening_results キーが見つかりません"
        assert isinstance(
            response["screening_results"], list
        ), "screening_results は list である必要があります"

        for item in response["screening_results"]:
            assert "symbol" in item or "sec_code" in item, "symbol または sec_code キーが必要です"
            assert "evaluation_year" in item, "evaluation_year キーが必要です"
            assert "total_score" in item, "total_score キーが必要です"

    @staticmethod
    async def assert_screening_results_saved_to_db(
        se: AsyncSession, expected_count: int, tolerance: int = 1
    ) -> None:
        """
        DB の screening_results に期待数のレコードが保存されているか確認

        Args:
            se: AsyncSession インスタンス
            expected_count: 期待されるレコード数
            tolerance: 許容誤差（デフォルト: 1）

        Raises:
            AssertionError: 保存確認失敗時
        """
        from app.models.screening.screening_result import ScreeningResult

        query = select(func.count(ScreeningResult.id))
        result = await se.execute(query)
        count = result.scalar() or 0

        assert (
            abs(count - expected_count) <= tolerance
        ), f"expected ~{expected_count} records, got {count}"

    @staticmethod
    def assert_financial_metrics_validity(result: Dict[str, Any]) -> None:
        """
        スクリーニング結果のスコアが妥当範囲か検証

        Args:
            result: screening result の辞書

        Raises:
            AssertionError: スコア検証失敗時
        """
        assert "total_score" in result, "total_score が見つかりません"
        assert (
            result["total_score"] >= 0
        ), f"Invalid total_score: {result['total_score']} (must be >= 0)"

        # オプショナルなスコア項目
        if "score_eps" in result:
            assert result["score_eps"] >= 0, f"Invalid score_eps: {result['score_eps']}"
            assert (
                result["score_eps"] <= result["total_score"]
            ), f"score_eps > total_score: {result['score_eps']} > {result['total_score']}"

        if "score_dividend" in result:
            assert (
                result["score_dividend"] >= 0
            ), f"Invalid score_dividend: {result['score_dividend']}"
            assert result["score_dividend"] <= result["total_score"], "score_dividend > total_score"

        if "score_stability" in result and result["score_stability"] is not None:
            assert result["score_stability"] >= 0, "Invalid score_stability"

        if "score_profitability" in result and result["score_profitability"] is not None:
            assert result["score_profitability"] >= 0, "Invalid score_profitability"

    @staticmethod
    def assert_no_data_loss(input_count: int, output_count: int, margin_pct: float = 0.05) -> None:
        """
        入力データ数 vs 出力カウント の乖離をチェック（5%許容）

        Args:
            input_count: 入力レコード数
            output_count: 出力レコード数
            margin_pct: 許容乖離率（デフォルト: 5%）

        Raises:
            AssertionError: データ損失検出時
        """
        if input_count == 0:
            return

        loss_pct = abs(input_count - output_count) / input_count
        assert (
            loss_pct <= margin_pct
        ), f"Data loss {loss_pct * 100:.1f}% exceeds tolerance {margin_pct * 100:.1f}%"

    @staticmethod
    def assert_result_sorted_by_score(results: List[Dict[str, Any]]) -> None:
        """
        スクリーニング結果が total_score でソート済みか（降順）検証

        Args:
            results: screening results の辞書リスト

        Raises:
            AssertionError: ソート検証失敗時
        """
        if not results:
            return

        scores = [r.get("total_score", 0) for r in results]
        sorted_scores = sorted(scores, reverse=True)

        assert (
            scores == sorted_scores
        ), f"Results not sorted by total_score (descending)\nGot: {scores}\nExpected: {sorted_scores}"

    @staticmethod
    def assert_sec_codes_filter(results: List[Dict[str, Any]], requested_codes: List[str]) -> None:
        """
        返却結果の sec_code が要求値と一致するか検証

        Args:
            results: screening results の辞書リスト
            requested_codes: 要求した証券コードリスト

        Raises:
            AssertionError: フィルタ検証失敗時
        """
        if not requested_codes:
            return

        returned_codes = set()
        for item in results:
            if "sec_code" in item:
                returned_codes.add(item["sec_code"])
            elif "symbol" in item:
                returned_codes.add(item["symbol"])

        requested_set = set(requested_codes)
        assert (
            returned_codes == requested_set
        ), f"Returned codes {returned_codes} != requested {requested_set}"

    @staticmethod
    def assert_evaluation_year_matches(results: List[Dict[str, Any]], evaluation_year: int) -> None:
        """
        スクリーニング結果の evaluation_year が期待値と一致するか検証

        Args:
            results: screening results の辞書リスト
            evaluation_year: 期待される評価年度

        Raises:
            AssertionError: 年度検証失敗時
        """
        for item in results:
            assert "evaluation_year" in item, "evaluation_year キーが見つかりません"
            assert (
                item["evaluation_year"] == evaluation_year
            ), f"evaluation_year mismatch: {item['evaluation_year']} != {evaluation_year}"

    @staticmethod
    def assert_response_contains_eligible_stocks(
        results: List[Dict[str, Any]], min_count: int = 1
    ) -> None:
        """
        レスポンスに最低限の適格銘柄が含まれているか検証

        Args:
            results: screening results の辞書リスト
            min_count: 最小銘柄数

        Raises:
            AssertionError: 銘柄数検証失敗時
        """
        eligible = [
            r for r in results if r.get("status") != "not_eligible" and r.get("total_score", 0) > 0
        ]
        assert (
            len(eligible) >= min_count
        ), f"Expected at least {min_count} eligible stocks, got {len(eligible)}"
