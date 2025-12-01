"""
API層 - 依存性注入プロバイダ

FastAPIのDependsパターンを使用したRepository提供を定義する。
共通モジュール（app.utils.database）のget_db()を使用してDBセッションを取得する。

仕様書: docs/architecture/layers/data_access_layer.md 3.3章
"""
