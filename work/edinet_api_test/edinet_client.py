"""EDINET API を試すための簡易クライアント。
標準ライブラリのみで動作する最小実装サンプル。

使い方:
    python work/edinet_api_test/edinet_client.py

環境変数:
    EDINET_BASE_URL: EDINET API のベースURL (省略時は公式推奨の想定URL)
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


class EdinetClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = base_url or os.environ.get(
            "EDINET_BASE_URL", "https://disclosure.edinet-fsa.go.jp/api/v1"
        )

    def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        with urllib.request.urlopen(url) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset)
            return json.loads(body)

    def get_documents(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """EDINETのドキュメントリストを取得するラッパー。
        params は EDINET API のクエリパラメータを想定。
        """
        return self._get("documents.json", params=params)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="EDINET API 簡易クライアントサンプル"
    )
    parser.add_argument(
        "--q", help="検索クエリ（例: code=0101）", default=None
    )
    args = parser.parse_args()

    client = EdinetClient()
    params = {}
    if args.q:
        # 簡易的に q=... を渡す (実運用では正しいパラメタ名を使用すること)
        params = dict(
            [seg.split("=") for seg in args.q.split(",") if "=" in seg]
        )
    try:
        res = client.get_documents(params=params or None)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"HTTP リクエストエラー: {e}")
