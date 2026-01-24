EDINET API 実験用スケルトン

目的:
- EDINET API を手軽に実行して挙動を確認するための最小限のサンプルコード。

ファイル:
- edinet_client.py: 標準ライブラリのみで GET を実行する簡易クライアント。

使い方:
1. (必要に応じて) 環境変数 `EDINET_BASE_URL` を設定する。
2. Python3 が有効な環境で次を実行:

```powershell
python work/edinet_api_test/edinet_client.py --q "code=7203"
```

備考:
- 実際の EDINET API のパラメータ名・挙動は公式仕様に合わせて調整してください。
- 本スケルトンは外部依存を増やさないため標準ライブラリのみを使用しています。必要なら `requests` 等を導入してください。
