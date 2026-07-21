"""
Convert cac file Excel P&L -> Parquet.
Moi thang co data moi, chay lai script nay.
File parquet luu vao folder data va copy sang folder code.
"""
import pandas as pd
import os
import shutil

FOLDER_PATH   = r"X:\Finance 2.Controlling\Dashboard\AI_PnL_rawdata"
DASHBOARD_DIR = r"C:\AI_Dashboard"
OUTPUT_FILE   = os.path.join(DASHBOARD_DIR, "pnl_cache.parquet")

# Kiem tra ket noi o mang X truoc khi chay
if not os.path.isdir(FOLDER_PATH):
    print("=" * 60)
    print("KHONG TRUY CAP DUOC O MANG X!")
    print(f"Duong dan: {FOLDER_PATH}")
    print("Kiem tra: 1) O X da ket noi chua?  2) Mo This PC xem co thay o X khong?")
    print("=" * 60)
    raise SystemExit

print("Doc cac file Excel P&L tu o X...")

excel_files = [
    os.path.join(FOLDER_PATH, f)
    for f in os.listdir(FOLDER_PATH)
    if f.endswith((".xlsx", ".xls", ".xlsm"))
]

print(f"Tim thay {len(excel_files)} file:")
for f in excel_files:
    print(f"  - {os.path.basename(f)}")

if not excel_files:
    print("\nKHONG tim thay file Excel nao! Kiem tra lai duong dan.")
    raise SystemExit

dfs = []
for f in excel_files:
    print(f"Dang doc {os.path.basename(f)}...")
    dfs.append(pd.read_excel(f))

df = pd.concat(dfs, ignore_index=True)
df.columns = df.columns.str.strip()

if "Month" in df.columns:
    months = sorted(df["Month"].dropna().unique().tolist())
    print(f"\nCac thang co trong data: {months}")

print(f"\nTong cong: {len(df):,} rows, {len(df.columns)} columns")
print("Dang luu Parquet...")

df.to_parquet(OUTPUT_FILE, index=False)
print(f"  -> Da luu: {OUTPUT_FILE}")

size_mb = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
print(f"\nXONG! Kich thuoc: {size_mb:.1f} MB")
print("Buoc tiep theo:")
print("  1. Restart app local de kiem tra")
print("  2. Upload pnl_cache.parquet len GitHub")
