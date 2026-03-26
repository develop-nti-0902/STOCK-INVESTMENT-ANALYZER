#!/usr/bin/env python3
"""
日経225のデータ最大期間取得テスト
期間を指定せずに、yfinanceから取得可能な全データを確認
"""

import sys

import yfinance as yf


def test_max_period():
    """期間を指定しない場合のデータ取得"""
    print("=" * 60)
    print("日経225 - 最大期間データ取得テスト")
    print("=" * 60)
    print(f"\n実行環境: {sys.executable}\n")

    print("[1] 期間指定なし（全利用可能データ）でダウンロード中...")
    nikkei_max = yf.download("^N225")

    print("\n✓ ダウンロード成功！\n")
    print("データサマリー:")
    print(f"期間: {nikkei_max.index.min().date()} ～ {nikkei_max.index.max().date()}")
    print(f"総データ行数: {len(nikkei_max)}")
    print(f"カラム: {list(nikkei_max.columns)}")

    print("\n\nデータ詳細:")
    print(f"日数：{(nikkei_max.index.max() - nikkei_max.index.min()).days} 日間")

    print("\n最初の5行:")
    print(nikkei_max.head())

    print("\n\n最後の5行:")
    print(nikkei_max.tail())

    print("\n" + "=" * 60)
    print(f"✓ 最大 {len(nikkei_max)} 行分のデータが取得できました")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_max_period()
    except Exception as e:
        print("\n✗ エラーが発生しました")
        print(f"エラー: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
