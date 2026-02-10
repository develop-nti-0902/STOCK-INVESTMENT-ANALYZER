import datetime

# flake8: noqa
import os
import re
import sys
import warnings
import zipfile
from glob import glob
from typing import List, Optional

import pandas as pd
import requests
from bs4 import XMLParsedAsHTMLWarning
from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser

# suppress noisy third-party warnings (bs4 XML-as-HTML)
# and SyntaxWarning from xbrl package
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning, module=".*xbrl.*")

# APIのエンドポイント
baseUrl = "https://disclosure.edinet-fsa.go.jp/api/v2"
docUrl = f"{baseUrl}/documents.json"

log_path = os.path.join("work", "edinet_api_test", "edinet_client2_output.txt")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
# 上書きモードで出力（実行ごとに新しい内容にする）
sys.stdout = open(log_path, "w", encoding="utf-8")
sys.stderr = sys.stdout


def extract_and_save(results, keys, out_path):
    """指定されたキーのみを抽出してdataFrameに変換し、CSVファイルに保存する.

    Args:
        results (list): `data["results"]` に該当するオブジェクトのリスト
        keys (list): 抽出するキー名のリスト
        out_path (str): 出力ファイルパス

    Returns:
        pd.DataFrame: 抽出したデータのDataFrame
    """
    extracted = [{k: item.get(k) for k in keys} for item in results]
    extracted = extracted[:200]
    extracted_df = pd.DataFrame(extracted)

    # 抽出結果をCSVに保存
    extracted_df.to_csv(
        out_path,
        index=False,
        encoding="utf-8-sig",
    )

    return extracted_df


def extract_securities_reports(
    submission_info_df: pd.DataFrame,
) -> pd.DataFrame:
    """有価証券報告書（受益証券を除く）を抽出してDataFrameで返す.

    条件:
    - `docDescription` が None でない
    - `docDescription` に「有価証券報告書」を含む
    - `docDescription` に「受益証券」を含まない

    Args:
        submission_info_df (pd.DataFrame): 少なくとも `docDescription` カラムを含むDataFrame

    Returns:
        pd.DataFrame: 抽出結果（該当なしの場合は空のDataFrame）
    """
    if submission_info_df is None or len(submission_info_df) == 0:
        return pd.DataFrame()

    # docDescriptionがNaNでない行を対象に検索
    desc = submission_info_df.get("docDescription")
    if desc is None:
        return pd.DataFrame()

    # NaNやNoneがあると .str.contains が扱いにくいため、安全に空文字に置換して検索する
    desc_safe = desc.fillna("").astype(str)
    contains_report = desc_safe.str.contains("有価証券報告書", na=False)
    contains_beneficiary = desc_safe.str.contains("受益証券", na=False)
    mask = contains_report & ~contains_beneficiary
    result_df = submission_info_df[mask].copy()

    if result_df.empty:
        print("有価証券報告書の提出情報がありません。")
    else:
        print("%d 件の有価証券報告書が抽出されました。" % len(result_df))

    return result_df


def download_document(
    doc_id: str,
    out_dir: str = "work/edinet_api_test/downloads",
    doc_type: int = 1,
) -> Optional[str]:
    """指定の `doc_id` をダウンロードしてファイルに保存する.

    Args:
        doc_id: ドキュメントID（例: 'S100N8ST'）
        out_dir: 保存先ディレクトリ
        doc_type: ダウンロード時に渡す `type` パラメータ（API仕様に従う、例: 1）

    Returns:
        保存したファイルパス（失敗時は None）
    """
    endpoint = f"{baseUrl}/documents/{doc_id}"
    params = {
        "type": doc_type,
        "Subscription-Key": "edff30e4028e4ba2a5871f8330cc1230",
    }

    document_response = requests.get(endpoint, params=params)

    if document_response.status_code != 200:
        print("Failed to download %s: status %s" % (doc_id, document_response.status_code))
        return None

    # 帰ってきたデータをzip形式で保存する
    zip_file_path = os.path.join(out_dir, doc_id + ".zip")
    with open(zip_file_path, "wb") as f:
        for chunk in document_response.iter_content(chunk_size=1024):
            f.write(chunk)

    os.makedirs(os.path.join(out_dir, doc_id), exist_ok=True)
    with zipfile.ZipFile(zip_file_path) as zip_f:
        zip_f.extractall(os.path.join(out_dir, doc_id))

    return document_response


def find_xbrl_files(doc_id: str, out_dir: str = "work/edinet_api_test/downloads") -> List[str]:
    """ダウンロード済みフォルダ内で PublicDoc 配下の .xbrl を再帰検索してパス一覧を返す.

    Args:
        doc_id: ドキュメントID
        out_dir: ダウンロード保存先のルートディレクトリ

    Returns:
        xbrl ファイルパスのリスト（見つからなければ空リスト）
    """
    pattern = os.path.join(out_dir, doc_id, "**", "PublicDoc", "**", "*.xbrl")
    paths = glob(pattern, recursive=True)
    if paths:
        print("Found %d xbrl file(s) for %s" % (len(paths), doc_id))
    else:
        print("No xbrl files found for %s" % doc_id)
    return paths


def get_context_candidates_from_text(txt: str, candidate_contexts: List[str]) -> List[str]:
    found = set(re.findall(r'contextRef="([^"]+)"', txt))
    context_candidates: List[str] = []
    for cand in candidate_contexts:
        for f in sorted(found):
            if cand in f and f not in context_candidates:
                context_candidates.append(f)
    for cand in candidate_contexts:
        if cand not in context_candidates:
            context_candidates.append(cand)
    return context_candidates


def extract_current_year_instant_date(xbrl_path: str) -> Optional[str]:
    """XBRL ファイルから CurrentYearInstant 系の context に対応する日付を抽出する."""
    try:
        with open(xbrl_path, "r", encoding="utf-8") as fh:
            txt = fh.read()
        # コンテキスト候補の優先順
        candidate_contexts = [
            "CurrentYearInstant",
            "CurrentYearInstant_ConsolidatedMember",
            "CurrentYearInstant_NonConsolidatedMember",
        ]
        ctxs = get_context_candidates_from_text(txt, candidate_contexts)
        # contexts は contextRef の id 候補。実際の <context id="..."> ブロックを探し instant を抽出する
        for cid in ctxs:
            pattern = (
                rf'<xbrli:context[^>]*id="{re.escape(cid)}"'
                r"[\s\S]*?<xbrli:instant>([^<]+)</xbrli:instant>"
            )
            m = re.search(pattern, txt)
            if m:
                return m.group(1)
        # フォールバック: 単純に最初の instant を返す
        m2 = re.search(r"<xbrli:instant>([^<]+)</xbrli:instant>", txt)
        if m2:
            return m2.group(1)
        return None
    except Exception:
        return None


def parse_report_metrics(xbrl_path: str) -> dict:
    """複数の指標を一括で解析して辞書で返す.

    戻り値キー: total_assets, net_assets, shareholders_equity, retained_earnings,
    short_term_loans, long_term_loans, bps, equity_to_asset_ratio

    ※短期借入金情報文字列（見つからなければ None）
    当期の短期借入金は短期借入金(タグ: jppfs_cor:ShortTermLoansPayable)と
    当期長期借入金の返済予定金額(タグ: jppfs_cor:CurrentPortionOfLongTermLoansPayable)の合算値となる

    銀行向けには別のタグが利用されているよう。ひとまず、銀行向け情報は無視する。タグとしては以下があるらしい。
    jppfs_cor:BorrowedMoneyLiabilitiesBNK
    jppfs_cor:BorrowedMoneyFromTrustAccountLiabilitiesBNK
    jppfs_cor:DepositsLiabilitiesBNK
    jppfs_cor:CurrentDepositsDepositsLiabilitiesBNK
    jppfs_cor:TimeDepositsDepositsLiabilitiesBNK
    jppfs_cor:NegotiableCertificatesOfDepositLiabilitiesBNK
    jppfs_cor:ProvisionForReimbursementOfDepositsLiabilitiesBNK

    """
    parser = EdinetXbrlParser()
    parsed_xbrl = parser.parse_file(xbrl_path)

    # フィールドごとの候補タグ
    field_candidates = {
        "total_assets": [
            "jpcrp_cor:TotalAssetsSummaryOfBusinessResults",
        ],
        "net_assets": [
            "jpcrp_cor:NetAssetsSummaryOfBusinessResults",
            "jppfs_cor:NetAssets",
        ],
        "shareholders_equity": [
            "jppfs_cor:ShareholdersEquity",
            "jppfs_cor:NetAssets",
        ],
        "retained_earnings": [
            "jppfs_cor:RetainedEarnings",
        ],
        "short_term_loans": [
            "jppfs_cor:ShortTermLoansPayable",
        ],
        "long_term_loans": [
            "jppfs_cor:LongTermLoansPayable",
        ],
        "bps": [
            "jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResults",
        ],
        "equity_to_asset_ratio": [
            "jpcrp_cor:EquityToAssetRatioSummaryOfBusinessResults",
        ],
    }

    # 優先するコンテキスト候補
    candidate_contexts = [
        "CurrentYearInstant",
        "CurrentYearInstant_ConsolidatedMember",
        "CurrentYearInstant_NonConsolidatedMember",
    ]

    # ファイルテキストから context 候補リストを組み立て
    try:
        with open(xbrl_path, "r", encoding="utf-8") as fh:
            txt = fh.read()
        context_candidates = get_context_candidates_from_text(txt, candidate_contexts)
    except Exception:
        context_candidates = candidate_contexts.copy()

    results: dict = {}
    for field, keys in field_candidates.items():
        found_val = None
        # 短期借入金は長期返済予定分を合算する場合があるので個別処理
        if field == "short_term_loans":
            vals = []
            # ShortTermLoansPayable
            for k in keys:
                for ctx in context_candidates:
                    info = parsed_xbrl.get_data_by_context_ref(k, ctx)
                    if info:
                        v = info.get_value()
                        if v is not None:
                            try:
                                vals.append(float(v))
                            except Exception:
                                pass
            # CurrentPortionOfLongTermLoansPayable をサブ的にチェックして加算
            for k2 in ["jppfs_cor:CurrentPortionOfLongTermLoansPayable"]:
                for ctx in context_candidates:
                    info2 = parsed_xbrl.get_data_by_context_ref(k2, ctx)
                    if info2:
                        v2 = info2.get_value()
                        if v2 is not None:
                            try:
                                vals.append(float(v2))
                            except Exception:
                                pass
            if vals:
                found_val = sum(vals)
        else:
            for k in keys:
                for ctx in context_candidates:
                    info = parsed_xbrl.get_data_by_context_ref(k, ctx)
                    if not info:
                        continue
                    v = info.get_value()
                    if v is None:
                        continue
                    try:
                        found_val = float(v)
                    except Exception:
                        found_val = v
                    break
                if found_val is not None:
                    break
        results[field] = found_val

    return results


def build_dataframe_from_metrics(metrics: dict, date_str: Optional[str]) -> pd.DataFrame:
    """指定順で DataFrame を作る.

    カラム順: 月日, 総資産, 純資産, 株主資本, 利益剰余金, 短期借入金, 長期借入金, BPS, 自己資本比率
    """
    # equity ratio が 0..1 の形式ならパーセント化
    eq = metrics.get("equity_to_asset_ratio")
    if eq is not None:
        try:
            f = float(eq)
            if abs(f) <= 1.5:
                metrics["equity_to_asset_ratio"] = f * 100.0
            else:
                metrics["equity_to_asset_ratio"] = f
        except Exception:
            pass

    row = {
        "date": date_str or "",
        "total_assets": metrics.get("total_assets"),
        "net_assets": metrics.get("net_assets"),
        "shareholders_equity": metrics.get("shareholders_equity"),
        "retained_earnings": metrics.get("retained_earnings"),
        "short_term_loans": metrics.get("short_term_loans"),
        "long_term_loans": metrics.get("long_term_loans"),
        "bps": metrics.get("bps"),
        "equity_to_asset_ratio": metrics.get("equity_to_asset_ratio"),
    }
    df = pd.DataFrame([row])
    return df


def make_day_list(start: datetime.date, end: datetime.date) -> List[datetime.date]:
    """start から end までの日付リスト（inclusive）を返す."""
    if start > end:
        return []
    days = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur = cur + datetime.timedelta(days=1)
    return days


start_date = datetime.date(2025, 6, 25)
end_date = datetime.date(2025, 6, 25)
stock_code = "42740"

# 日付リストを作成（datetime.date のリスト）
day_list = make_day_list(start_date, end_date)

for day in day_list:
    fmt_day = day.strftime("%Y-%m-%d")

    # パラメータの設定（例: 2024年5月17日の書類を取得）
    params = {
        "date": fmt_day,  # 取得したい日付
        "type": 2,  # 2は有価証券報告書などの決算書類
        "Subscription-Key": "edff30e4028e4ba2a5871f8330cc1230",
    }

    # APIリクエストを送信
    response = requests.get(docUrl, params=params)

    # レスポンスのJSONデータを取得
    data = response.json()

    # 抽出するキーをリストで渡す
    selected_keys = [
        "formCode",
        "docID",
        "edinetCode",
        "secCode",
        "filerName",
        "docDescription",
    ]
    out_path = "work/edinet_api_test/selected_fields.csv"
    # 抽出して保存。DataFrameで欲しいので return_df=True にする（ダウンロード直後からDataFrameで扱える）
    submission_info_df = extract_and_save(data.get("results", []), selected_keys, out_path)
    # ダウンロード件数が0件の場合はスキップ
    if submission_info_df.empty:
        continue

    # secCodeがnullのデータは除外し、指定したstock_codeのデータのみ抽出する
    # submission_info_df = submission_info_df[
    #     (submission_info_df["secCode"].notnull())
    #     & (submission_info_df["secCode"] == stock_code)
    # ]

    submission_info_df = submission_info_df[(submission_info_df["secCode"].notnull())]

    print("Saved selected fields to %s (items: %d)" % (out_path, len(submission_info_df)))

    # 有価証券報告書を抽出
    securities_reports_df = extract_securities_reports(submission_info_df)
    print(securities_reports_df)
    # 抽出結果をCSVに保存
    securities_reports_df.to_csv(
        "work/edinet_api_test/securities_reports.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print("Saved securities reports to work/edinet_api_test/securities_reports.csv")

    # mainルートから download_document を呼び出す（将来の拡張を想定して現状の関数を利用）
    if not securities_reports_df.empty:
        # work\edinet_api_test\downloads配下に年/月/日フォルダを作成して保存
        out_dir = os.path.join(
            "work",
            "edinet_api_test",
            "downloads",
            day.strftime("%Y/%m/%d"),
        )
        os.makedirs(out_dir, exist_ok=True)

        # docID -> secCode マップ（出力時に現在の銘柄コードを表示するため）
        docid_to_seccode = securities_reports_df.set_index("docID")["secCode"].to_dict()

        for doc_id in securities_reports_df["docID"]:
            print("#################################")
            try:
                resp = download_document(doc_id, out_dir=out_dir)
                # download_document は将来拡張されるため、現状はレスポンスオブジェクトを返す想定
                if resp is None:
                    print(f"download_document returned None for {doc_id}")
                else:
                    status = getattr(resp, "status_code", "N/A")
                    print("Called download_document for %s, status=%s" % (doc_id, status))
                # スクレイピング対象の XBRL ファイルの存在を確認
                xbrl_paths = find_xbrl_files(doc_id, out_dir=out_dir)
                if xbrl_paths:
                    for p in xbrl_paths:
                        print("  xbrl: %s" % p)
                        # 現在処理中の銘柄コードを表示
                        sec_code = docid_to_seccode.get(doc_id)
                        print("  secCode: %s" % sec_code)
                    # 先頭の XBRL を解析して各メトリクスを抽出、DataFrame を作成して保存
                    try:
                        metrics = parse_report_metrics(xbrl_paths[0])
                        date_str = extract_current_year_instant_date(xbrl_paths[0])
                        df_metrics = build_dataframe_from_metrics(metrics, date_str)
                        if df_metrics is None or df_metrics.empty:
                            print("  metrics: None (no matching tags)")
                        else:
                            rec = df_metrics.to_dict(orient="records")[0]
                            print("  metrics: %s" % rec)
                            out_csv = os.path.join(
                                "work",
                                "edinet_api_test",
                                "parsed_metrics.csv",
                            )
                            if not os.path.exists(out_csv):
                                df_metrics.to_csv(out_csv, index=False, encoding="utf-8-sig")
                            else:
                                df_metrics.to_csv(
                                    out_csv,
                                    mode="a",
                                    header=False,
                                    index=False,
                                    encoding="utf-8-sig",
                                )
                    except Exception as e:
                        print(f"  metrics extraction error: {e}")
                else:
                    print("  no xbrl found for %s" % doc_id)
            except Exception as e:
                print("Error calling download_document for %s: %s" % (doc_id, e))
    else:
        print("No securities reports to download.")
