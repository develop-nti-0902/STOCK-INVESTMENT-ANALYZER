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
from dotenv import load_dotenv
from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser

# .envファイルから環境変数を読み込み
load_dotenv()

# suppress noisy third-party warnings (bs4 XML-as-HTML)
# and SyntaxWarning from xbrl package
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning, module=".*xbrl.*")

# APIのエンドポイント
baseUrl = "https://disclosure.edinet-fsa.go.jp/api/v2"
docUrl = f"{baseUrl}/documents.json"

# --- ログ出力先へ標準出力/標準エラーをリダイレクト ---

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
        "Subscription-Key": os.getenv("EDINET_SUBSCRIPTION_KEY", ""),
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
    pattern = f"{out_dir}/{doc_id}/**/PublicDoc/**/*.xbrl"
    paths = glob(pattern, recursive=True)
    if paths:
        print("Found %d xbrl file(s) for %s" % (len(paths), doc_id))
    else:
        print("No xbrl files found for %s" % doc_id)
    return paths


def parse_report_dividend_paid_per_share(xbrl_path: str) -> Optional[dict]:
    """指定した XBRL ファイルを解析し、指定した情報を返す.

    Args:
        xbrl_path: XBRL ファイルのパス

    Returns:
        １株当たり配当額情報文字列（見つからなければ None）
    """
    try:
        parser = EdinetXbrlParser()
        parsed_xbrl = parser.parse_file(xbrl_path)

        # 総資産の候補タグ（優先順）
        candidate_keys = [
            "jpcrp_cor:DividendPaidPerShareSummaryOfBusinessResults",
        ]

        # 優先するコンテキスト候補を明示的に定義（汎用 → 連結 → 個別）
        candidate_contexts = [
            "CurrentYearDuration",
            "CurrentYearDuration_ConsolidatedMember",
            "CurrentYearDuration_NonConsolidatedMember",
        ]

        # XBRL ファイル内に定義されている contextRef を読み、
        # 定義済み候補の順でマッチするものを優先リストとして作成する
        context_candidates: List[str]
        try:
            with open(xbrl_path, "r", encoding="utf-8") as fh:
                txt = fh.read()
            found = set(re.findall(r'contextRef="([^"]+)"', txt))
            context_candidates = []
            for cand in candidate_contexts:
                for f in sorted(found):
                    if cand in f and f not in context_candidates:
                        context_candidates.append(f)
            # 見つからなかった候補はリスト末尾に付ける（解析時に試すため）
            for cand in candidate_contexts:
                if cand not in context_candidates:
                    context_candidates.append(cand)
        except Exception:
            context_candidates = candidate_contexts.copy()

        # 明示的に優先度順の候補リストを作る（キー優先→コンテキスト優先）
        candidate_pairs = [(k, c) for k in candidate_keys for c in context_candidates]
        for key, ctx in candidate_pairs:
            info = parsed_xbrl.get_data_by_context_ref(key, ctx)
            if not info:
                continue
            val = info.get_value()
            if val is None:
                continue
            return {"tag": key, "context": ctx, "raw_value": val}

        return None
    except Exception as e:
        print("Error parsing XBRL %s: %s" % (xbrl_path, e))
        return None


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


start_date = datetime.date(2025, 6, 20)
end_date = datetime.date(2025, 6, 20)
stock_code = "83160"

# 日付リストを作成（datetime.date のリスト）
day_list = make_day_list(start_date, end_date)

for day in day_list:
    fmt_day = day.strftime("%Y-%m-%d")

    # パラメータの設定（例: 2024年5月17日の書類を取得）
    params = {
        "date": fmt_day,  # 取得したい日付
        "type": 2,  # 2は有価証券報告書などの決算書類
        "Subscription-Key": os.getenv("EDINET_SUBSCRIPTION_KEY", ""),
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
    submission_info_df = submission_info_df[
        (submission_info_df["secCode"].notnull()) & (submission_info_df["secCode"] == stock_code)
    ]

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
        out_dir = os.path.join("work", "edinet_api_test", "downloads", day.strftime("%Y/%m/%d"))
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
                    # 先頭の XBRL を解析して決算末日情報を取得
                    try:
                        info = parse_report_dividend_paid_per_share(xbrl_paths[0])
                        if info is None:
                            print("  info: None (no matching tag/context)")
                        else:
                            raw = info.get("raw_value")
                            print(
                                "  info: tag=%s, context=%s, raw=%s"
                                % (info.get("tag"), info.get("context"), raw)
                            )
                    except Exception as e:
                        print("  dividend parse error: %s" % e)
                else:
                    print("  no xbrl found for %s" % doc_id)
            except Exception as e:
                print("Error calling download_document for %s: %s" % (doc_id, e))
    else:
        print("No securities reports to download.")
