#!/usr/bin/env python3
"""yfinanceの異なるパラメータ指定方法を比較"""

import yfinance as yf

print("=" * 60)
print("yfinance パラメータ比較実験")
print("=" * 60)

print("\n[方法1] period='max' のみ")
try:
    df1 = yf.download("^N225", period="max", progress=False)
    print(f"取得データ: {len(df1)} 行")
    if len(df1) > 0:
        print(f"期間: {df1.index[0]} ～ {df1.index[-1]}")
except Exception as e:
    print(f"エラー: {e}")

print("\n[方法2] start/end 指定（古い日付から今日まで）")
try:
    df2 = yf.download("^N225", start="1990-01-01", progress=False)
    print(f"取得データ: {len(df2)} 行")
    if len(df2) > 0:
        print(f"期間: {df2.index[0]} ～ {df2.index[-1]}")
except Exception as e:
    print(f"エラー: {e}")

print("\n[方法3] interval='1d' + period='max'")
try:
    df3 = yf.download("^N225", period="max", interval="1d", progress=False)
    print(f"取得データ: {len(df3)} 行")
    if len(df3) > 0:
        print(f"期間: {df3.index[0]} ～ {df3.index[-1]}")
except Exception as e:
    print(f"エラー: {e}")

print("\n[方法4] interval='1d' + start/end 指定")
try:
    df4 = yf.download("^N225", start="1990-01-01", interval="1d", progress=False)
    print(f"取得データ: {len(df4)} 行")
    if len(df4) > 0:
        print(f"期間: {df4.index[0]} ～ {df4.index[-1]}")
except Exception as e:
    print(f"エラー: {e}")

print("\n[方法5] auto_adjust=False なし")
try:
    df5 = yf.download("^N225", period="max", interval="1d", progress=False)
    print(f"取得データ: {len(df5)} 行")
    if len(df5) > 0:
        print(f"期間: {df5.index[0]} ～ {df5.index[-1]}")
except Exception as e:
    print(f"エラー: {e}")

print("\n[方法6] start/end指定, auto_adjust=False")
try:
    df6 = yf.download("^N225", start="1990-01-01", interval="1d", progress=False, auto_adjust=False)
    print(f"取得データ: {len(df6)} 行")
    if len(df6) > 0:
        print(f"期間: {df6.index[0]} ～ {df6.index[-1]}")
except Exception as e:
    print(f"エラー: {e}")

print("\n" + "=" * 60)
