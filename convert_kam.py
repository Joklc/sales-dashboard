"""
Convert file MTD_KAM.xlsx (bang phang chi tiet, co 2 goc nhin KAM & FIN)
-> 1 file Parquet: kam_cache.parquet.
Snapshot, khong theo thang. Moi lan co file moi, chay lai script nay.

Khac get_data: file nay co 2 bo so lieu costing
  - KAM: Net + COGS + SGM theo goc Key Account
  - FIN: Net + COGS + SGM theo goc Finance
Net 2 goc gan nhu nhau, khac chu yeu o COGS -> SGM.
Khong co Family 2, khong co ten khach (chi ma khach).
"""
import pandas as pd
import os
import shutil

INPUT_FILE    = r"X:\Finance 2.Controlling\Dashboard\AI_KAM_rawdata\MTD_KAM.xlsx"
DASHBOARD_DIR = r"C:\AI_Dashboard"
OUTPUT_FILE   = os.path.join(DASHBOARD_DIR, "kam_cache.parquet")

# Kiem tra ket noi o mang X truoc khi chay
RAWDATA_DIR = os.path.dirname(INPUT_FILE)
if not os.path.isdir(RAWDATA_DIR):
    print("=" * 60)
    print("KHONG TRUY CAP DUOC O MANG X!")
    print(f"Duong dan: {RAWDATA_DIR}")
    print("Kiem tra: 1) O X da ket noi chua?  2) Mo This PC xem co thay o X khong?")
    print("=" * 60)
    raise SystemExit

print("Doc file MTD_KAM.xlsx tu o X...")

if not os.path.exists(INPUT_FILE):
    print(f"KHONG tim thay file: {INPUT_FILE}")
    raise SystemExit

# Header that o dong 6 (index 5), data tu dong 7
raw = pd.read_excel(INPUT_FILE, sheet_name="Summary", header=5)
raw = raw.dropna(axis=1, how="all")

# ==================================================
# LAM SACH: bo dong rong, dong header lap, dong toan so 0
# ==================================================
df = raw[raw["Item code"].notna()].copy()
df = df[~df["Item code"].astype(str).isin(["Item code", "0", "0.0"])]
df = df[~df["CHANNEL NAME"].astype(str).isin(["CHANNEL NAME", "0", "0.0"])]

# Doi ten cot ve chuan
df = df.rename(columns={
    "Customer code":                 "Customer",
    "CHANNEL NAME":                  "Channel",
    "MLA NAME":                      "MLA",
    "Product Line":                  "Product Line",
    "Item code":                     "Item code",
    "Comm. code":                    "Comm code",
    "Item name":                     "Item name",
    "Sum of Quantity":               "Qty",
    "Sum of Line Totalafter All DC": "Gross",
    "NET SALE_KAM":                  "Net_KAM",
    "COGS_KAM":                      "COGS_KAM",
    "NET SALE_FIN":                  "Net_FIN",
    "COGS_FIN":                      "COGS_FIN",
})

# Ep so
for c in ["Qty", "Gross", "Net_KAM", "COGS_KAM", "Net_FIN", "COGS_FIN"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Tinh san SGM (so tien) cho ca 2 goc = Net - COGS
df["SGM_KAM"] = df["Net_KAM"] - df["COGS_KAM"]
df["SGM_FIN"] = df["Net_FIN"] - df["COGS_FIN"]

# Cot text
for c in ["Customer", "Channel", "MLA", "Product Line", "Item code", "Comm code", "Item name"]:
    df[c] = df[c].astype(str).replace("nan", "")

keep = ["Channel", "MLA", "Customer", "Product Line", "Item code", "Comm code",
        "Item name", "Qty", "Gross", "Net_KAM", "SGM_KAM", "Net_FIN", "SGM_FIN"]
df = df[keep].copy()

# As of = thoi diem chay convert
as_of = pd.Timestamp.now()
df["As_of"] = as_of

# ==================================================
# KIEM TRA NHANH
# ==================================================
def pct(n, d): return n / d * 100 if d else 0
g = df["Gross"].sum()
print(f"\nAs of: {as_of:%d-%b-%Y %H:%M}")
print(f"So dong chi tiet: {len(df)}")
print(f"So Channel: {df['Channel'].nunique()} | MLA: {df['MLA'].nunique()} | Item: {df['Item code'].nunique()}")
print(f"Tong Gross  : {g:,.0f}")
print(f"[KAM] Net {df['Net_KAM'].sum():,.0f} | SGM% {pct(df['SGM_KAM'].sum(), df['Net_KAM'].sum()):.2f}%")
print(f"[FIN] Net {df['Net_FIN'].sum():,.0f} | SGM% {pct(df['SGM_FIN'].sum(), df['Net_FIN'].sum()):.2f}%")

# ==================================================
# LUU
# ==================================================
df.to_parquet(OUTPUT_FILE, index=False)
print(f"\n  -> Da luu: {OUTPUT_FILE}")

print("\nXONG!")
print("Buoc tiep: 1) Restart app  2) Upload kam_cache.parquet len GitHub")
