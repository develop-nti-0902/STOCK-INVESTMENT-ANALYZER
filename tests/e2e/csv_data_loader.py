"""CSV データから E2E テスト用 EDINET データを DB に投入するローダー."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import insert, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)


@dataclass
class LoadResult:
    """CSV ロード結果"""

    model_name: str
    records_loaded: int
    records_skipped: int
    errors: List[str]


class EdinetCsvDataLoader:
    """EDINET E2E テストデータを CSV から DB に投入するローダー"""

    def __init__(self, session: AsyncSession):
        """Initialize loader with async session."""
        self._session = session

    async def load_edinet_test_data(
        self,
        source_csv_paths: Dict[str, Path],
        sec_codes: Optional[List[str]] = None,
        fiscal_years: Optional[List[int]] = None,
    ) -> Dict[str, LoadResult]:
        """
        複数の CSV ファイルからテストデータを一括投入

        Args:
            source_csv_paths: {model_name: csv_path}
                - "profit_and_loss" -> Path(...)
                - "cash_flow_statement" -> Path(...)
                - "stock_dividend" -> Path(...)
                - "stock_master" -> Path(...) [optional]
            sec_codes: フィルタ対象の証券コード（None → すべて）
            fiscal_years: フィルタ対象の会計年度（None → すべて）

        Returns:
            {model_name: LoadResult, ...}

        Raises:
            FileNotFoundError: CSV ファイルが見つかりない
            ValueError: CSV パースエラー
        """
        from app.models.market_data.edinet.edinet_cash_flow_statement import EdinetCashFlowStatement
        from app.models.market_data.edinet.edinet_profit_and_loss import EdinetProfitAndLoss
        from app.models.market_data.edinet.edinet_stock_dividend import EdinetStockDividend
        from app.models.market_data.stock_master.stock_master import StockMaster
        from app.repositories.market_data.edinet import EdinetDocumentRepository

        results = {}

        # マッピング: CSV キー → SQLAlchemy モデル
        model_mapping: Dict[str, Type] = {
            "stock_master": StockMaster,
            "profit_and_loss": EdinetProfitAndLoss,
            "cash_flow_statement": EdinetCashFlowStatement,
            "stock_dividend": EdinetStockDividend,
        }

        # StockMaster は依存なし（事前投入）
        if "stock_master" in source_csv_paths:
            csv_path = source_csv_paths["stock_master"]
            stock_models = self._parse_csv_to_models(csv_path, StockMaster, sec_codes, fiscal_years)
            loaded_count = await self._batch_insert(stock_models)
            results["stock_master"] = LoadResult(
                model_name="stock_master",
                records_loaded=loaded_count,
                records_skipped=len(stock_models) - loaded_count,
                errors=[],
            )

        # ===== 1. EdinetDocument を先行投入 =====
        # CSV から EDINET メタデータを抽出してドキュメントレコードを事前投入
        edinet_doc_map: Dict[str, int] = {}  # doc_id → edinet_document.id
        edinet_repo = EdinetDocumentRepository(self._session)

        # 全 EDINET CSV から doc_id の一覧を抽出
        edinet_csv_keys = ["profit_and_loss", "cash_flow_statement", "stock_dividend"]
        all_doc_ids_metadata = {}  # doc_id → {sec_code, submission_date, ...}

        for key in edinet_csv_keys:
            if key not in source_csv_paths:
                continue
            csv_path = source_csv_paths[key]
            if not csv_path.exists():
                raise FileNotFoundError(f"CSV ファイルが見つかりません: {csv_path}")

            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    doc_id = row.get("doc_id")
                    if not doc_id or doc_id in all_doc_ids_metadata:
                        continue  # 既に記録済み or 空
                    # メタデータを集約
                    all_doc_ids_metadata[doc_id] = {
                        "sec_code": row.get("sec_code"),
                        "submission_date": row.get("submission_date"),
                        "report_type": row.get("report_type", "annual"),
                        "candidate_contexts": row.get("candidate_contexts"),
                        "candidate_keys": row.get("candidate_keys"),
                    }

        # EdinetDocument を create_or_get で投入
        for doc_id, metadata in all_doc_ids_metadata.items():
            # submission_date を date 型に変換
            from datetime import datetime

            submission_date_str = metadata["submission_date"]
            submission_date = datetime.strptime(submission_date_str, "%Y-%m-%d").date()

            # create_or_get で既存or新規作成
            edinet_doc = await edinet_repo.create_or_get(
                doc_id=doc_id,
                sec_code=metadata["sec_code"],
                submission_date=submission_date,
                report_type=metadata["report_type"],
                candidate_contexts=metadata["candidate_contexts"],
                candidate_keys=metadata["candidate_keys"],
            )
            edinet_doc_map[doc_id] = edinet_doc.id

        # ===== 2. EDINET テーブル投入（P&L → CF → Dividend）=====
        all_models: Dict[str, List[Any]] = {}
        for key in edinet_csv_keys:
            if key not in source_csv_paths:
                continue

            csv_path = source_csv_paths[key]
            model_class = model_mapping[key]
            models = self._parse_csv_to_models_with_fk(
                csv_path, model_class, edinet_doc_map, sec_codes, fiscal_years
            )
            all_models[key] = models

        # 財務整合性チェック (3つのテーブルが揃っている場合)
        if len(all_models) == 3:
            self._validate_financial_integrity(
                all_models.get("profit_and_loss", []),
                all_models.get("cash_flow_statement", []),
                all_models.get("stock_dividend", []),
            )

        # 各テーブルへ投入
        for key, models in all_models.items():
            loaded_count = await self._batch_insert(models)
            results[key] = LoadResult(
                model_name=key,
                records_loaded=loaded_count,
                records_skipped=len(models) - loaded_count,
                errors=[],
            )

        return results

    @staticmethod
    def _parse_csv_to_models(
        csv_path: Path,
        model_class: Type[T],
        sec_codes: Optional[List[str]] = None,
        fiscal_years: Optional[List[int]] = None,
    ) -> List[T]:
        """
        CSV パースと SQLAlchemy モデル変換

        Args:
            csv_path: CSV ファイルパス
            model_class: ターゲットモデルクラス
            sec_codes: フィルタ対象の証券コード
            fiscal_years: フィルタ対象の会計年度

        Returns:
            パース済みモデルインスタンスリスト
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV ファイルが見つかりません: {csv_path}")

        models: List[T] = []
        errors: List[str] = []

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # ヘッダー行をスキップ
                try:
                    # フィルタリング
                    if sec_codes and row.get("sec_code") not in sec_codes:
                        continue
                    if fiscal_years and row.get("fiscal_year"):
                        if int(row["fiscal_year"]) not in fiscal_years:
                            continue

                    # 型変換
                    converted_row = EdinetCsvDataLoader._convert_row_types(row, model_class)
                    model_instance = model_class(**converted_row)
                    models.append(model_instance)

                except ValueError as e:
                    errors.append(f"行 {row_num} でのパースエラー: {str(e)}")
                except Exception as e:
                    errors.append(f"行 {row_num} での予期しないエラー: {str(e)}")

        if errors:
            # ログに出力するが、処理は継続
            for error in errors:
                print(f"⚠️  {error}")

        return models

    @staticmethod
    def _parse_csv_to_models_with_fk(
        csv_path: Path,
        model_class: Type[T],
        edinet_doc_map: Dict[str, int],
        sec_codes: Optional[List[str]] = None,
        fiscal_years: Optional[List[int]] = None,
    ) -> List[T]:
        """
        CSV パースと SQLAlchemy モデル変換（FK 対応版）

        EdinetDocument との外部キー参照が必要な EDINET テーブル用。
        doc_id から edinet_document_id を取得してモデルに設定します。

        Args:
            csv_path: CSV ファイルパス
            model_class: ターゲットモデルクラス
            edinet_doc_map: doc_id → edinet_document.id のマッピング
            sec_codes: フィルタ対象の証券コード
            fiscal_years: フィルタ対象の会計年度

        Returns:
            パース済みモデルインスタンスリスト
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV ファイルが見つかりません: {csv_path}")

        models: List[T] = []
        errors: List[str] = []

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # ヘッダー行をスキップ
                try:
                    # フィルタリング
                    if sec_codes and row.get("sec_code") not in sec_codes:
                        continue
                    if fiscal_years and row.get("fiscal_year"):
                        if int(row["fiscal_year"]) not in fiscal_years:
                            continue

                    # doc_id から edinet_document_id を取得
                    doc_id = row.get("doc_id")
                    if not doc_id or doc_id not in edinet_doc_map:
                        raise ValueError(f"Unknown doc_id: {doc_id}")
                    row["edinet_document_id"] = edinet_doc_map[doc_id]

                    # 型変換
                    converted_row = EdinetCsvDataLoader._convert_row_types(row, model_class)
                    model_instance = model_class(**converted_row)
                    models.append(model_instance)

                except ValueError as e:
                    errors.append(f"行 {row_num} でのパースエラー: {str(e)}")
                except Exception as e:
                    errors.append(f"行 {row_num} での予期しないエラー: {str(e)}")

        if errors:
            # ログに出力するが、処理は継続
            for error in errors:
                print(f"⚠️  {error}")

        return models

    @staticmethod
    def _convert_row_types(row: Dict[str, str], model_class: Type[T]) -> Dict[str, Any]:
        """
        CSV レコード（すべて文字列）を SQLAlchemy モデルの型定義に基づいて変換

        Args:
            row: CSV から読み込んだ行（Dict[str, str]）
            model_class: ターゲットモデルクラス

        Returns:
            型変換済みの Dict
        """
        converted = {}

        # SQLAlchemy の列情報を取得
        mapper = inspect(model_class)
        columns = {col.name: col for col in mapper.columns}

        for key, value in row.items():
            if key not in columns:
                # モデルに存在しないカラムはスキップ
                continue

            col = columns[key]

            # 空文字列 → None（NULL）
            if value is None or value == "":
                converted[key] = None
                continue

            # 型変換ロジック
            col_type_str = str(col.type).lower()

            try:
                if "integer" in col_type_str or "biginteger" in col_type_str:
                    converted[key] = int(value)
                elif "numeric" in col_type_str or "decimal" in col_type_str:
                    # 小数点以下2桁に丸める
                    decimal_val = Decimal(str(value))
                    converted[key] = decimal_val.quantize(Decimal("0.01"))
                elif "date" in col_type_str:
                    # YYYY-MM-DD 形式
                    from datetime import datetime

                    parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
                    converted[key] = parsed_date
                elif "boolean" in col_type_str:
                    # "true"/"false"/"1"/"0" など
                    if value.lower() in ("true", "1", "yes"):
                        converted[key] = True
                    elif value.lower() in ("false", "0", "no"):
                        converted[key] = False
                    else:
                        converted[key] = bool(int(value))
                else:
                    # VARCHAR など → そのまま
                    converted[key] = value
            except (ValueError, TypeError) as e:
                raise ValueError(f"カラム '{key}' の型変換失敗: {value} → {col_type_str}: {e}")

        return converted

    @staticmethod
    def _validate_financial_integrity(
        pl_models: List[Any],
        cf_models: List[Any],
        dividend_models: List[Any],
    ) -> bool:
        """
        P&L、CF、Dividend の財務整合性チェック

        検証項目:
        - eps < net_sales（EPS が売上高を超えない）
        - operating_cf > 0（営業CF が正値）
        - dividend_adj > 0（配当が正値）

        Args:
            pl_models: EdinetProfitAndLoss インスタンスリスト
            cf_models: EdinetCashFlowStatement インスタンスリスト
            dividend_models: EdinetStockDividend インスタンスリスト

        Returns:
            True if valid, raises ValueError otherwise
        """
        # PL: EPS vs 売上高
        for pl in pl_models:
            if pl.eps and pl.net_sales:
                if pl.eps > pl.net_sales:
                    raise ValueError(
                        f"EPS > net_sales: {pl.edinet_document_id} " f"({pl.eps} > {pl.net_sales})"
                    )

        # CF: 営業CF は正値
        for cf in cf_models:
            if cf.operating_cf and cf.operating_cf < 0:
                raise ValueError(
                    f"Negative operating_cf: {cf.edinet_document_id} ({cf.operating_cf})"
                )

        # Dividend: 配当は正値
        for div in dividend_models:
            if div.dividend_adj and div.dividend_adj < 0:
                raise ValueError(
                    f"Negative dividend_adj: {div.edinet_document_id} ({div.dividend_adj})"
                )

        return True

    async def _batch_insert(
        self,
        models: List[T],
        batch_size: int = 100,
    ) -> int:
        """
        バッチ挿入（パフォーマンス最適化）

        Args:
            models: 投入するモデルインスタンスリスト
            batch_size: バッチサイズ（デフォルト: 100）

        Returns:
            投入レコード数
        """
        if not models:
            return 0

        inserted_count = 0

        # バッチ処理でデータ投入
        for i in range(0, len(models), batch_size):
            batch = models[i : i + batch_size]
            try:
                # SQLAlchemy の insert() + execute()
                stmt = insert(models[0].__class__).values([self._model_to_dict(m) for m in batch])
                result = await self._session.execute(stmt)
                inserted_count += result.rowcount or len(batch)
            except Exception:
                # 重複キーなどのエラーは1行ずつ再試行
                for model in batch:
                    try:
                        self._session.add(model)
                        await self._session.flush()
                        inserted_count += 1
                    except Exception as skip_err:
                        # スキップ（既に存在するなど）
                        print(f"⚠️  スキップ: {skip_err}")
                        continue

        await self._session.commit()
        return inserted_count

    @staticmethod
    def _model_to_dict(model: T) -> Dict[str, Any]:
        """SQLAlchemy モデルを辞書に変換"""
        mapper = inspect(model.__class__)
        return {col.name: getattr(model, col.name) for col in mapper.columns}
