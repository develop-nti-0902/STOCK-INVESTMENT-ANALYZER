#!/usr/bin/env python3
"""
日経225データ取得テスト
yfinanceから日経225の日足データが取得できるか確認
"""

import sys

import yfinance as yf

try:
    print("=" * 60)
    print("日経225データ取得テスト")
    print("=" * 60)
    print(f"\n実行環境: {sys.executable}\n")

    print("ダウンロード中...")
    nikkei = yf.download("^N225", start="2020-01-01", end="2025-01-01")

    print("\n✓ ダウンロード成功！\n")
    print("データヘッド（最初の5行）:")
    print(nikkei.head())

    print("\n\nデータサマリー:")
    print(f"期間: {nikkei.index.min().date()} ～ {nikkei.index.max().date()}")
    print(f"総データ行数: {len(nikkei)}")
    print(f"カラム: {list(nikkei.columns)}")

    print("\n\nデータ型:")
    print(nikkei.dtypes)

    print("\n" + "=" * 60)
    print("✓ 日経225データは正常に取得できました！")
    print("=" * 60)

except Exception as e:
    print("\n✗ エラーが発生しました")
    print(f"エラー: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
