"""EDINET 向けドキュメント処理の集約サービス.

当モジュールはダウンロード→パース→複数パーサの実行→保存の一連処理を提供します。
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from lxml import etree
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.data_synchronization.market_data.edinet.download_service import (
    EdinetDownloadService,
)

logger = logging.getLogger(__name__)


class EdinetAggregateUpdateService:
    """複数パーサを用いたドキュメント処理をオーケストレーションするサービス."""

    def __init__(
        self,
        download_service: Optional[EdinetDownloadService] = None,
        parser_saver_pairs: Optional[
            List[
                Tuple[
                    Callable[[etree._Element], Dict[str, Any]], Any, Callable[[Dict[str, Any]], Any]
                ]
            ]
        ] = None,
        dividend_metrics_service: Optional[Any] = None,
    ) -> None:
        """サービスは予め処理する `parser` と `saver` の組み合わせを保持します.

        - `parser_saver_pairs` は `(parser_callable, converter, saver_callable)` のリストを想定します。
                - `parser_callable` は `Callable[[etree._Element], Dict[str, Any]]` を提供すること。
                - `converter` はパーサ出力を pydantic モデルに変換するインターフェースを提供する。
                    （例: `to_pydantic` / `from_pydantic` を持つことを想定）
                - `saver_callable` は `Callable[[Dict[str, Any]], Awaitable[Any]]` を期待します。
        """
        self.download_service = download_service or EdinetDownloadService()
        self.parser_saver_pairs: List[
            Tuple[Callable[[etree._Element], Dict[str, Any]], Any, Callable[[Dict[str, Any]], Any]]
        ] = (parser_saver_pairs or [])
        self.dividend_metrics_service = dividend_metrics_service

    async def process_document(
        self,
        doc_id: str,
        session: Optional[AsyncSession] = None,
        transaction_atomic: bool = True,
        sec_code: Optional[str] = None,
        submission_date: Optional[Any] = None,
        filer_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ダウンロードを一度だけ行い、パース→各パーサ実行→保存を行います.

        カウントと各パーサの結果を含むサマリ辞書を返します。
        注意: `transaction_atomic` が True の場合、呼び出し側は同一の `AsyncSession` を
        引数 `session` として渡してください。セーバはそのセッションを利用する前提です。
        """
        extracted_path: Optional[Path] = None
        summary: Dict[str, Any] = {"doc_id": doc_id, "results": []}

        try:
            ##########################################################
            # ドキュメント取得・抽出（ここで1回だけダウンロード/解凍を実行）
            # - `download_and_extract` を呼び、抽出結果のファイル/ディレクトリパスを取得します。
            # - 以降の全てのパーサはこの抽出成果物を共有して解析を行います。
            ##########################################################
            _download_start = time.perf_counter()
            extracted_path = await self.download_service.download_and_extract(doc_id)
            _download_time = time.perf_counter() - _download_start
            _db_op_start = time.perf_counter()

            ##########################################################
            # XBRL のパース（ここで1回だけ lxml によるパースを行う）
            # - ブロッキング処理のためスレッドで実行し、得られた root を各パーサに渡します。
            ##########################################################
            def _parse() -> etree._Element:
                parser = etree.parse(str(extracted_path))
                return parser.getroot()

            root = await asyncio.to_thread(_parse)

            # parser_saver_pairs はサービスに予め設定されたものを使用する
            # 各要素は (parser_callable, converter, saver_callable) の3タプルを要求します。
            parser_saver_pairs = self.parser_saver_pairs

            # NOTE: トランザクションは呼び出し側（例: process_date_range の日付単位トランザクション）で
            # 管理する想定に変更しました。ここではコミット/ロールバックを行わず、単に各パーサ/セーバを
            # 実行して結果サマリを返します。

            ##########################################################
            # 各パーサの実行とセーバ呼び出し（ここで各シートの更新を依頼）
            # - `parser_saver_pairs` の順に沿って、各パーサに対して同一の `root` を渡して解析させます。
            # - 返却された辞書（parsed）を対応するセーバに渡し、DB 保存を行います。
            # - `transaction_atomic=True` の場合は以下のブロック内で一括コミット（原子操作）を行います。
            ##########################################################
            if not parser_saver_pairs:
                raise RuntimeError(
                    "no parser_saver_pairs configured for EdinetAggregateUpdateService"
                )

            # ここで一度だけ parsed_xbrl を作成して各パーサに渡す
            try:
                from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser as XbrlParser

                def _build_parsed():
                    xp = XbrlParser()
                    return xp.parse_file(str(extracted_path))

                parsed_xbrl = await asyncio.to_thread(_build_parsed)
            except Exception:
                parsed_xbrl = None

            # datetime/date のトップレベル import を利用

            def _normalize_date(v: Any) -> Any:
                """提出日フォーマットを可能な限り日付オブジェクトに正規化する."""
                if v is None:
                    return None
                # datetime -> date
                if isinstance(v, datetime):
                    return v.date()
                # date (without time) -> keep
                if isinstance(v, date) and not isinstance(v, datetime):
                    return v
                # string parsing attempts
                if isinstance(v, str):
                    try:
                        return datetime.fromisoformat(v).date()
                    except Exception:
                        try:
                            # try splitting off time portion
                            return datetime.fromisoformat(v.split()[0]).date()
                        except Exception:
                            return v
                return v

            async def _process_entry(entry):
                # entry: (parser, converter, saver) を想定
                try:
                    if not isinstance(entry, (list, tuple)):
                        raise TypeError(
                            "parser_saver entry must be a tuple/list of (parser, converter, saver)"
                        )

                    if len(entry) != 3:
                        raise TypeError(
                            "parser_saver entry must be a 3-tuple: (parser, converter, saver)"
                        )

                    parser_callable, converter, saver_callable = entry

                    # まず (root, parsed_xbrl) で parser を呼び、失敗したら root のみで呼ぶ
                    try:
                        parsed = parser_callable(root, parsed_xbrl)
                    except TypeError:
                        parsed = parser_callable(root)

                    # converter 経路: converter で saver に渡すペイロードを構築する
                    saver_payloads: list[Dict[str, Any]] = []

                    if isinstance(parsed, dict):
                        # 年次マップ (値が dict または None) と単一レコードを判定
                        is_year_map = all(
                            (v is None or isinstance(v, dict)) for v in parsed.values()
                        )
                        if is_year_map:
                            for _, year_data in parsed.items():
                                if not year_data:
                                    continue
                                enriched = {
                                    **year_data,
                                    "doc_id": doc_id,
                                    "sec_code": sec_code,
                                    "submission_date": submission_date,
                                    "filer_name": filer_name,
                                }
                                # normalize keys expected by converters
                                # period_end_date は各パーサで正規化して返すため、ここでの補完は不要
                                # normalize submission_date to date if possible
                                if enriched.get("submission_date") is not None:
                                    enriched["submission_date"] = _normalize_date(
                                        enriched.get("submission_date")
                                    )
                                model = converter.to_pydantic(enriched)
                                saver_payloads.append(converter.from_pydantic(model))
                        else:
                            enriched = {
                                **parsed,
                                "doc_id": doc_id,
                                "sec_code": sec_code,
                                "submission_date": submission_date,
                                "filer_name": filer_name,
                            }
                            # period_end_date は各パーサで正規化して返すため、ここでの補完は不要
                            if enriched.get("submission_date") is not None:
                                enriched["submission_date"] = _normalize_date(
                                    enriched.get("submission_date")
                                )
                            model = converter.to_pydantic(enriched)
                            saver_payloads.append(converter.from_pydantic(model))
                    else:
                        # フォールバック: 単一レコードとして変換を試みる
                        enriched = {
                            "doc_id": doc_id,
                            "sec_code": sec_code,
                            "submission_date": submission_date,
                            "filer_name": filer_name,
                        }
                        # period_end_date は各パーサで正規化して返すため、ここでの補完は不要
                        if enriched.get("submission_date") is not None:
                            enriched["submission_date"] = _normalize_date(
                                enriched.get("submission_date")
                            )
                        model = converter.to_pydantic(enriched)
                        saver_payloads.append(converter.from_pydantic(model))

                    # saver_callable にディスパッチ - 複数ペイロード時はバッチを優先
                    if not saver_payloads:
                        return {
                            "parser": getattr(parser_callable, "__name__", repr(parser_callable)),
                            "status": "ok",
                            "saved": None,
                        }

                    try:
                        if len(saver_payloads) == 1:
                            saved = await saver_callable(saver_payloads[0])
                        else:
                            # 所有者が `save_batch` を持つ場合はそちらを使い、なければ個別に呼ぶ
                            owner = getattr(saver_callable, "__self__", None)
                            if owner is not None and hasattr(owner, "save_batch"):
                                saved = await owner.save_batch(saver_payloads)
                            else:
                                results = []
                                for payload in saver_payloads:
                                    results.append(await saver_callable(payload))
                                saved = results
                        return {
                            "parser": getattr(parser_callable, "__name__", repr(parser_callable)),
                            "status": "ok",
                            "saved": saved,
                        }
                    except Exception:
                        logger.exception("saver failed for doc %s", doc_id)
                        raise

                except Exception as exc:
                    logger.exception("parser/converter/saver failed for doc %s: %s", doc_id, exc)
                    # Safely obtain parser name from the entry tuple (avoid getattr with non-string)
                    try:
                        parser_name = getattr(entry[0], "__name__", repr(entry[0]))
                    except Exception:
                        parser_name = repr(entry)
                    return {
                        "parser": parser_name,
                        "status": "error",
                        "error": str(exc),
                    }

            # ここではトランザクションを開始せず、各エントリを順次処理して結果を集める。
            # トランザクション制御（コミット／SAVEPOINT／ロールバック）は呼び出し側に委ねる。
            for entry in parser_saver_pairs:
                res = await _process_entry(entry)
                if res is None:
                    continue
                summary["results"].append(res)
            summary["metrics"] = {
                "download_time_seconds": _download_time,
                "db_operation_time_seconds": time.perf_counter() - _db_op_start,
            }

            return summary
        finally:
            # 抽出された成果物は成功/失敗にかかわらず必ずクリーンアップを試みる
            if extracted_path is not None:
                try:
                    self.download_service.cleanup(Path(extracted_path))
                except Exception:
                    logger.exception("抽出成果物のクリーンアップに失敗しました: %s", doc_id)

    async def process_date_range(
        self,
        start_date: "date",
        end_date: "date",
        progress_interval: int = 10,
        max_documents: int | None = None,
        session: Optional[AsyncSession] = None,
        transaction_atomic: bool = True,
    ) -> Dict[str, Any]:
        """指定期間の EDINET ドキュメントを検索して順次処理するバッチメソッド.

        - `start_date`/`end_date` は date オブジェクトを想定します。
        - 内部で `download_service.fetcher.search_documents` を用いて日次で検索します。
        - 各ドキュメントごとに `process_document` を呼び出します。
        """
        # use top-level timedelta import

        ##########################################################
        # ドキュメント検索・収集
        # - 指定期間の各日について EDINET API を呼び出し、対象となるドキュメントを収集します。
        # - ここでは `download_service.fetcher.search_documents` を日次で呼び出して
        #   年次報告（docTypeCode == "120"）などの対象リストを作成します。
        ##########################################################
        all_documents: list[dict[str, Any]] = []
        current_date = start_date
        _search_start = time.perf_counter()
        while current_date <= end_date:
            try:
                docs = await self.download_service.search_documents(current_date)
                annual_reports = [
                    doc
                    for doc in docs
                    if doc.get("docTypeCode") == "120"
                    and doc.get("secCode") is not None
                    and "受益証券" not in doc.get("docDescription", "")
                ]
                all_documents.extend(annual_reports)
            except Exception:
                logger.warning("Failed to search documents for %s", current_date)
            current_date += timedelta(days=1)
        _search_time = time.perf_counter() - _search_start

        ##########################################################
        # ドキュメント数制限（オプション）
        # - `max_documents` が指定されている場合、処理対象数を上限で切り詰めます。
        ##########################################################
        if max_documents is not None and len(all_documents) > max_documents:
            all_documents = all_documents[:max_documents]

        ##########################################################
        # 対象無し時の早期終了
        # - 検索結果が空の場合は処理せずに集計した空の結果を返します。
        ##########################################################
        total_docs = len(all_documents)
        if total_docs == 0:
            logger.info(
                "EDINET batch metrics",
                extra={
                    "total_download_time_seconds": _search_time,
                    "total_db_operation_time_seconds": 0.0,
                    "total_documents": 0,
                    "processed_documents": 0,
                    "saved_items": 0,
                    "failed_documents": 0,
                },
            )
            return {
                "status": "completed",
                "total_documents": 0,
                "processed_documents": 0,
                "saved_items": 0,
                "failed_documents": 0,
            }

        processed_docs = 0
        saved_items = 0
        failed_docs = 0
        failed_docs_details: list[Dict[str, Any]] = []
        total_download_time: float = 0.0
        total_db_operation_time: float = 0.0

        ##########################################################
        # 各ドキュメントの逐次処理
        # - 集めたドキュメントを順に `process_document` で処理します。
        # - 各ドキュメント処理の成否を集計し、保存件数をカウントします。
        # - 進捗は `progress_interval` ごとにログ出力します。
        ##########################################################
        # ドキュメント処理: 日付単位での原子トランザクションをサポート
        # - `transaction_atomic=True` の場合、呼び出し元から渡された `session` を
        #   日付（このバッチ全体）単位で `session.begin()` によるトランザクションでラップします。
        # - 各ドキュメント処理は `transaction_atomic=False` として呼び出し、
        #   パーサエラーが発生したら日付単位トランザクションを中止します。
        # `transaction_atomic=True` の場合は session が必須。
        # 外側で日付単位のトランザクションを張り、各ドキュメントは SAVEPOINT
        # （begin_nested）で保護して個別にロールバック可能にする。
        if transaction_atomic:
            if session is None:
                raise ValueError("session is required when transaction_atomic is True")
            # session is present here
            async with session.begin():
                for i, doc in enumerate(all_documents, start=1):
                    doc_id = doc.get("docID")
                    if not doc_id:
                        logger.warning("Document missing docID: %s", doc)
                        failed_docs += 1
                        continue

                    try:
                        async with session.begin_nested():
                            summary = await self.process_document(
                                doc_id,
                                session=session,
                                transaction_atomic=False,
                                sec_code=doc.get("secCode"),
                                submission_date=doc.get("submitDateTime"),
                                filer_name=doc.get("filerName"),
                            )

                            for r in summary.get("results", []):
                                if r.get("status") == "error":
                                    raise RuntimeError(
                                        f"parser error for doc {doc_id}: {r.get('error')}"
                                    )

                        for r in summary.get("results", []):
                            if "saved" not in r or r["saved"] is None:
                                continue
                            saved = r["saved"]
                            if isinstance(saved, list):
                                saved_items += len(saved)
                            else:
                                saved_items += 1

                        _doc_metrics = summary.get("metrics", {})
                        total_download_time += _doc_metrics.get("download_time_seconds", 0.0)
                        total_db_operation_time += _doc_metrics.get(
                            "db_operation_time_seconds", 0.0
                        )
                        processed_docs += 1
                    except Exception as e:
                        logger.exception(
                            "Document processing failed and rolled back to savepoint doc_id=%s: %s",
                            doc_id,
                            e,
                        )
                        failed_docs += 1
                        failed_docs_details.append(
                            {
                                "doc_id": doc_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                        )

                    if i % progress_interval == 0:
                        logger.info(
                            "Progress: %d/%d documents processed, %d failed",
                            processed_docs,
                            total_docs,
                            failed_docs,
                        )
        else:
            for i, doc in enumerate(all_documents, start=1):
                doc_id = doc.get("docID")
                if not doc_id:
                    logger.warning("Document missing docID: %s", doc)
                    failed_docs += 1
                    continue

                try:
                    summary = await self.process_document(
                        doc_id,
                        session=session,
                        transaction_atomic=transaction_atomic,
                        sec_code=doc.get("secCode"),
                        submission_date=doc.get("submitDateTime"),
                        filer_name=doc.get("filerName"),
                    )

                    for r in summary.get("results", []):
                        if "saved" not in r or r["saved"] is None:
                            continue
                        saved = r["saved"]
                        if isinstance(saved, list):
                            saved_items += len(saved)
                        else:
                            saved_items += 1

                    _doc_metrics = summary.get("metrics", {})
                    total_download_time += _doc_metrics.get("download_time_seconds", 0.0)
                    total_db_operation_time += _doc_metrics.get("db_operation_time_seconds", 0.0)
                    processed_docs += 1
                except Exception as e:
                    logger.exception("Failed to process doc_id=%s: %s", doc_id, e)
                    failed_docs += 1
                    failed_docs_details.append(
                        {
                            "doc_id": doc_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )

                if i % progress_interval == 0:
                    logger.info(
                        "Progress: %d/%d documents processed, %d failed",
                        processed_docs,
                        total_docs,
                        failed_docs,
                    )

        ##########################################################
        # 配当メトリクス計算・保存
        # - 全ドキュメント処理後に、配当メトリクスを計算・保存します。
        ##########################################################
        dividend_metrics_result = {}
        if self.dividend_metrics_service and processed_docs > 0:
            try:
                logger.info("配当メトリクス計算・保存開始")
                # 処理済みドキュメントから sec_code を集約
                sec_codes_processed = set()
                for doc in all_documents[:processed_docs]:  # 処理済みドキュメントのみ
                    sec_code = doc.get("secCode")
                    if sec_code:
                        sec_codes_processed.add(sec_code)

                # 各証券コード毎に dividend レコードを検索・計算
                total_saved = 0
                for sec_code in sec_codes_processed:
                    try:
                        dividend_records = await self.dividend_metrics_service.dividend_repo.find_latest_by_sec_code(
                            sec_code
                        )
                        if dividend_records:
                            # 先ほどの find_latest_by_sec_code は Optional で単一値を返す
                            # 複数件を処理するために find_by_period を使うか、または
                            # 全員を処理するロジックに修正
                            # ここで簡潔に、単一レコードで処理
                            records_list = [dividend_records] if dividend_records else []
                            result_item = (
                                await self.dividend_metrics_service.compute_and_save_metrics(
                                    sec_code=sec_code,
                                    dividend_records=records_list,
                                )
                            )
                            total_saved += result_item.get("saved_records", 0)
                    except Exception as e:
                        logger.warning(f"配当メトリクス計算失敗 ({sec_code}): {e}")

                dividend_metrics_result = {
                    "status": "completed",
                    "total_sec_codes": len(sec_codes_processed),
                    "total_saved": total_saved,
                }
                logger.info(f"配当メトリクス計算・保存完了: {dividend_metrics_result}")
            except Exception as e:
                logger.exception("配当メトリクス処理に失敗: %s", e)
                dividend_metrics_result = {
                    "status": "error",
                    "error": str(e),
                }

        ##########################################################
        # バッチ集計の作成と返却
        # - 処理結果（総件数・処理済み件数・保存件数・失敗件数）を集計して返します。
        ##########################################################
        result = {
            "status": "completed",
            "total_documents": total_docs,
            "processed_documents": processed_docs,
            "saved_items": saved_items,
            "failed_documents": failed_docs,
            "failed_documents_details": failed_docs_details,
            "dividend_metrics": dividend_metrics_result,
        }
        logger.info(
            "EDINET batch metrics",
            extra={
                "total_download_time_seconds": _search_time + total_download_time,
                "total_db_operation_time_seconds": total_db_operation_time,
                "total_documents": total_docs,
                "processed_documents": processed_docs,
                "saved_items": saved_items,
                "failed_documents": failed_docs,
            },
        )
        logger.info("Batch completed: %s", result)
        return result


__all__ = ["EdinetAggregateUpdateService"]
