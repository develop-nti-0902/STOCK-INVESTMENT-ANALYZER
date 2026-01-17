# CORS 設定

このプロジェクトでは、FastAPI 側の CORS 設定を環境変数 `CORS_ORIGINS` で管理します。

- デフォルト開発用オリジン:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`

設定方法:

- カンマ区切りの環境変数をセットする例:

```powershell
$env:CORS_ORIGINS = "http://example.com,http://frontend.example.com"
```

- または JSON 配列文字列を指定することもできます:

```powershell
$env:CORS_ORIGINS = "[\"http://example.com\", \"http://frontend.example.com\"]"
```

注意:
- 本番環境ではワイルドカード `*` の利用は避け、実際のフロントエンドオリジンを明示的に指定してください。
- 認証を行う API では `allow_credentials=True` を有効にする必要があります。既に本プロジェクトでは `allow_credentials=True` が設定されています。
