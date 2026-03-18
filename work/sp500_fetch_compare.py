import pandas as pd
import requests

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
if resp.status_code != 200:
    raise SystemExit(f"Failed to fetch page: status={resp.status_code}")

try:
    df = pd.read_html(resp.text)[0]
except Exception as e:
    print("Failed to parse table from HTML:", e)
    raise

# Basic ticker list
if "Symbol" in df.columns:
    tickers = df["Symbol"].tolist()
else:
    # try common alternatives
    candidates = [c for c in df.columns if "symbol" in c.lower()]
    if candidates:
        tickers = df[candidates[0]].tolist()
    else:
        tickers = []

print("tickers_count:", len(tickers))
print("first10:", tickers[:10])

# Print DataFrame columns and a small preview of useful columns
print("\nDataFrame columns:", df.columns.tolist())

desired = [
    "Symbol",
    "Security",
    "SEC filings",
    "GICS Sector",
    "GICS Sub-Industry",
    "Headquarters Location",
    "Date first added",
    "CIK",
    "Founded",
]
available = [c for c in desired if c in df.columns]
print("\nAvailable columns for detailed preview:", available)

if available:
    print(df[available].head(10).to_string(index=False))
else:
    print(
        "No expected columns found for detailed preview. Here are first 5 rows:\n",
        df.head(5).to_string(index=False),
    )
