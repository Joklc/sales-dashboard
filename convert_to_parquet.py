"""
Chay script nay de convert Excel -> Parquet.
Moi thang khi co data moi, chay lai script nay.
File parquet se duoc luu vao CA 2 noi: folder data va folder code.
"""
import pandas as pd
import os
import shutil

FOLDER_PATH   = r"C:\AI_Sale_rawdata"
OUTPUT_FILE   = r"C:\AI_Sale_rawdata\data_cache.parquet"
DASHBOARD_DIR = r"C:\AI_Dashboard"

print("Doc cac file Excel...")

excel_files = [
    os.path.join(FOLDER_PATH, f)
    for f in os.listdir(FOLDER_PATH)
    if f.endswith((".xlsx", ".xls", ".xlsm"))
]

print(f"Tim thay {len(excel_files)} file:")
for f in excel_files:
    print(f"  - {os.path.basename(f)}")

if not excel_files:
    print("\nKHONG tim thay file Excel nao trong folder! Kiem tra lai duong dan.")
    raise SystemExit

dfs = []
for f in excel_files:
    print(f"Dang doc {os.path.basename(f)}...")
    dfs.append(pd.read_excel(f))

df = pd.concat(dfs, ignore_index=True)
df.columns = df.columns.str.strip()

# Kiem tra cac thang co trong data
if "MONTH" in df.columns:
    months = df["MONTH"].dropna().unique().tolist()
    print(f"\nCac thang co trong data: {months}")

print(f"\nTong cong: {len(df):,} rows, {len(df.columns)} columns")
print("Dang luu Parquet...")

# Luu vao folder data
df.to_parquet(OUTPUT_FILE, index=False)
print(f"  -> Da luu: {OUTPUT_FILE}")

# Copy luon sang folder code (de app.py local doc duoc)
dashboard_file = os.path.join(DASHBOARD_DIR, "data_cache.parquet")
if os.path.isdir(DASHBOARD_DIR):
    shutil.copy(OUTPUT_FILE, dashboard_file)
    print(f"  -> Da copy sang: {dashboard_file}")

size_mb = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
print(f"\nXONG! Kich thuoc: {size_mb:.1f} MB")
print("Buoc tiep theo:")
print("  1. Restart app local de kiem tra")
print("  2. Upload file data_cache.parquet moi len GitHub (de cloud cap nhat)")
