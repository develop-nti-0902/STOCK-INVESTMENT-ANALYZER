import datetime

# flake8: noqa
import os
import sys
import warnings
from typing import List

import pandas as pd
import requests
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

# suppress noisy third-party warnings
warnings.filterwarnings("ignore")

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

    初回実行時は新規作成、2回目以降は追記.

    Args:
        results (list): `data["results"]` に該当するオブジェクトのリスト
        keys (list): 抽出するキー名のリスト
        out_path (str): 出力ファイルパス

    Returns:
        pd.DataFrame: 抽出したデータのDataFrame
    """
    extracted = [{k: item.get(k) for k in keys} for item in results]
    extracted_df = pd.DataFrame(extracted)

    # 既存ファイルがあるかチェック
    if os.path.exists(out_path):
        # ファイルが存在する場合、追記モード（ヘッダーなし）
        with open(out_path, "a", encoding="utf-8-sig", newline="") as f:
            extracted_df.to_csv(f, index=False, header=False)
        print(f"Appended data to {out_path}")
    else:
        # ファイルが存在しない場合、新規作成（ヘッダーあり）
        extracted_df.to_csv(
            out_path,
            index=False,
            encoding="utf-8-sig",
        )
        print(f"Created new file: {out_path}")

    return extracted_df


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


start_date = datetime.date(2025, 6, 1)
end_date = datetime.date(2025, 6, 30)
stock_code = "42740"

# 日付リストを作成（datetime.date のリスト）
day_list = make_day_list(start_date, end_date)

for day in day_list:
    fmt_day = day.strftime("%Y-%m-%d")

    # パラメータの設定
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
    # 抽出して追記保存
    submission_info_df = extract_and_save(data.get("results", []), selected_keys, out_path)
    # ダウンロード件数が0件の場合はスキップ
    if submission_info_df.empty:
        print(f"No results for {fmt_day}")
        continue

    print(f"Processed {len(submission_info_df)} items for {fmt_day}")
