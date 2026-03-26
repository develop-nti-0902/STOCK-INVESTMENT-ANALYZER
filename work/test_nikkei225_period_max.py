#!/usr/bin/env python3
"""
日経225データ取得テスト - 期間指定の代わりに period=max を使用
"""

import sys

import yfinance as yf


def test_with_period_max():
    """period='max' を使ってデータ取得"""
    print("=" * 70)
    print("日経225 - period='max' を使用したデータ取得テスト")
    print("=" * 70)
    print(f"\n実行環境: {sys.executable}\n")

    print("[1] period='max' でダウンロード中...")
    nikkei = yf.download("^N225", period="max")

    print("\n✓ ダウンロード成功！\n")
    print("データサマリー:")
    print(f"期間: {nikkei.index.min().date()} ～ {nikkei.index.max().date()}")
    print(f"総データ行数: {len(nikkei)}")
    print(f"カラム: {list(nikkei.columns)}")

    print("\n最初の5行:")
    print(nikkei.head())

    print("\n\n最後の5行:")
    print(nikkei.tail())

    print("\n" + "=" * 70)
    print(f"✓ period='max' で {len(nikkei)} 行分のデータが取得できました")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_with_period_max()
    except Exception as e:
        print("\n✗ エラーが発生しました")
        print(f"エラー: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
