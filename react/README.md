# React フロントエンド（.js と .css で動作）

このフォルダは Vite を使った React 開発用です。ソースは `.js` と `.css`（`.module.css` 含む）で構成されており、`.jsx` 拡張子は使用していません。

セットアップ（Windows）:

```powershell
cd react
npm install
npm run dev
```

ビルド:

```powershell
npm run build
npm run preview
```

補足:
- `src/App.js` をエントリとして `src/main.js` でマウントします。
- 既存の `.js` / `.module.css` ファイルはそのまま動作するように設定しています。
