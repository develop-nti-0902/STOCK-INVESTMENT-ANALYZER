# EDINET documents.json のデータ構造（完全版）

## 概要
- トップレベルはオブジェクト（JSON object）で、必ず `metadata` と `results` を持ちます（本データでは両方存在）。
- `metadata` はレスポンスのメタ情報を含むオブジェクトです。
- `results` は各提出書類のメタデータを要素とする配列（JSON array）で、配列内の各要素は同一のキーセットを持ちます（本データでは258要素、キー数29）。

## トップレベル
- `metadata`: object
- `results`: array of object

---

## `metadata` フィールド
- `title` (string)
- `parameter` (object)
  - `date` (string, 例: "2024-05-17")
  - `type` (string, 本データでは "2")
- `resultset` (object)
  - `count` (integer, 本データでは 258)
- `processDateTime` (string, 例: "2026-01-24 00:00")
- `status` (string, 例: "200")
- `message` (string, 例: "OK")

各キーの説明（簡潔）:
- `title`: APIの名称
- `parameter`: リクエストパラメータの識別子
  - `date`: 指定したファイルの日付
  - `type`: 指定した取得情報(1:メタデータのみ、2:提出書類一覧及びメタデータを取得)
- `resultset`: 結果セットの識別子
  - `count`: 指定したファイル日付における提出書類一覧の件数
- `processDateTime`: 提出書類一覧の更新時間(提出書類一覧の内容に変更がない場合でも書類一覧更新日付は更新される)
- `status`: ステータスコード
- `message`: メッセージ


---

## `results` のオブジェクト（本データの各要素が持つすべてのキーと型）
配列内各オブジェクトは同一のキーセット（29キー）を持ちます。キーと型は以下の通りです。

- `seqNumber` (integer)
- `docID` (string)
- `edinetCode` (string)
- `secCode` (string or null)
- `JCN` (string or null)
- `filerName` (string)
- `fundCode` (string or null)
- `ordinanceCode` (string)
- `formCode` (string)
- `docTypeCode` (string)
- `periodStart` (string in YYYY-MM-DD or null)
- `periodEnd` (string in YYYY-MM-DD or null)
- `submitDateTime` (string in "YYYY-MM-DD hh:mm")
- `docDescription` (string)
- `issuerEdinetCode` (string or null)
- `subjectEdinetCode` (string or null)
- `subsidiaryEdinetCode` (string or null)
- `currentReportReason` (string or null)
- `parentDocID` (string or null)
- `opeDateTime` (string or null)
- `withdrawalStatus` (string)
- `docInfoEditStatus` (string)
- `disclosureStatus` (string)
- `xbrlFlag` (string)
- `pdfFlag` (string)
- `attachDocFlag` (string)
- `englishDocFlag` (string)
- `csvFlag` (string)
- `legalStatus` (string)

各キーの説明（簡潔）:
- `seqNumber`: ファイル日付ごとの連番
- `docID`: 書類識別番号（ダウンロードエンドポイントに渡す識別子）
- `edinetCode`: 提出者のEDINETコード
- `secCode`: 証券コード（上場企業のみ設定、無い場合は null）
- `JCN`: 会社法人番号（無い場合は null）
- `filerName`: 提出者の名称
- `fundCode`: 投資信託等のコード（該当なければ null）
- `ordinanceCode`: 府令コード
- `formCode`: 株式コード
- `docTypeCode`: 書類種別コード
- `periodStart` / `periodEnd`: 対象会計期間開始/終了日（無いケースあり）
- `submitDateTime`: 提出日時
- `docDescription`: 書類の説明文（タイトル等）
- `issuerEdinetCode`: 大量保有について発行会社のEDINETコード
- `subjectEdinetCode`: 公開買付けについて対象となるEDINETコード
- `subsidiaryEdinetCode`: 子会社のEDINETコード
- `currentReportReason`: 臨時報告書の提出自由
- `parentDocID`: 親書類のID（無い場合は null）
- `opeDateTime`: 内部操作日時等（無い場合は null）
- `withdrawalStatus`: 取下区分（1: 取下書、2: 取り下げられた書類、0: それ以外）
- `docInfoEditStatus`: 書類情報修正区分（1: 財務局職員が書類を修正した情報、2: 修正された書類、0: それ以外）
- `disclosureStatus`: 開示不開示区分（1: 財務局職員によって書類の不開示を開始した情報、2: 不開示とされている書類、3: 財務局職員によって書類の不開示を解除した情報、0: それ以外）
- `xbrlFlag`: XBRL有無フラグ（1: 有り、0: それ以外）
- `pdfFlag`: PDF有無フラグ（1: 有り、0: それ以外）
- `attachDocFlag`: 添付書類有無フラグ（1: 有り、0: それ以外）
- `englishDocFlag`: 英語書類有無フラグ（1: 有り、0: それ以外）
- `csvFlag`: CSV有無フラグ（1: 有り、0: それ以外）
- `legalStatus`: 縦覧区分（1: 縦覧中、2: 延長期間中、0: 閲覧期間満了）

---
