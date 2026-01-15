# STOCK-INVESTMENT-ANALYZER

このリポジトリは株価データの取得・保存・分析を行うサービスです。以下はローカルでの起動・開発・テスト手順の簡易ガイドです。

## 前提
- Python 3.9+ がインストールされていること
- 推奨: `poetry` を使った環境構築（プロジェクトは Poetry を前提としています）

## 開発環境の準備（Poetry）
```bash
poetry install
poetry shell
```

## 開発環境の準備（venv + pip）
```powershell
# PowerShell 例 (Windows)
& .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## サーバー起動（ローカル）
デフォルトでは `app.main:app` を uvicorn で起動します。

```bash
# 開発モード (ホットリロード有効)
python -m uvicorn app.main:app --reload --port 8000
# または Poetry を利用している場合
poetry run uvicorn app.main:app --reload --port 8000
```

起動後に以下のURLで自動生成ドキュメントを確認できます:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## フロントエンド起動（React）
```bash
cd react
npm install
npm start
```

起動後に `http://localhost:3000` でReactアプリにアクセスできます。

### 銘柄マスタ更新機能の使い方
1. バックエンドサーバーを起動 (上記の「サーバー起動」参照)
2. Reactアプリを起動
3. 画面の「データ連携設定」メニューに移動
4. 「銘柄マスタ管理」セクションで「銘柄マスタを更新」ボタンをクリック
5. JPXから最新の銘柄情報が取得され、データベースに保存されます

注: 初回実行時はデータ量が多いため、数分かかる場合があります。テスト用には「サンプル更新」ボタンを使うと100件のみ取得できます。

## テスト実行
```bash
# 全テスト
pytest

# 特定テストファイルを実行
pytest tests/unit/api/v1/test_batch.py -q
```

## 注意点
- 実際の外部API (Yahoo Finance 等) を使う統合テストはネットワークや認証情報が必要です。CI環境ではスキップされる場合があります。
- 実際に大量データを取得するバッチ処理はローカルでの実行負荷が高くなるため、テストではモックや小規模なパラメータで動作確認してください。

---
README を更新しました。詳しい開発フローや設計は `docs/` 以下を参照してください。
