import asyncio
import sqlite3
import sys

sys.path.insert(0, "F:/TAKUMI/GitHub/STOCK-INVESTMENT-ANALYZER")

conn = sqlite3.connect("F:/TAKUMI/DB/SQLite/stockdb_test.db")
cur = conn.cursor()

print("=== stock_master (all rows) ===")
cur.execute("SELECT stock_code, is_active, stock_name FROM stock_master")
for r in cur.fetchall():
    print(f"  {r}")

print("\n=== stocks_1d count for 1301 ===")
cur.execute("SELECT COUNT(*) FROM stocks_1d WHERE symbol = '1301'")
print(cur.fetchone())

print("\n=== relative_strength count for 1301 ===")
cur.execute("SELECT COUNT(*) FROM relative_strength WHERE symbol = '1301'")
print(cur.fetchone())

print("\n=== relative_strength latest 3 for 1301 ===")
cur.execute(
    "SELECT symbol, calculation_date, relative_strength_score FROM relative_strength WHERE symbol='1301' ORDER BY calculation_date DESC LIMIT 3"
)
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
