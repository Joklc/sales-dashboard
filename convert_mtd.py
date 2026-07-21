"""
Convert file get_data.xlsx (bang phang chi tiet) -> 1 file Parquet duy nhat.
Day la snapshot (khong theo thang). Moi lan co file moi, chay lai script nay.

KHAC ban cu: file nay la bang phang, moi dong = 1 item cua 1 khach.
Tat ca bang tong (Channel / MLA / Product Line / Family 2) se duoc trang
tu tinh bang groupby -> nen loc duoc theo moi chieu. Khong con file
mtd_productline.parquet / mtd_family2.parquet nua.
"""
import pandas as pd
import os
import shutil

# Doi duong dan neu folder ban o cho khac
FOLDER        = r"X:\Finance 2.Controlling\Dashboard\AI_MTD_rawdata"
DASHBOARD_DIR = r"C:\AI_Dashboard"
OUTPUT_FILE   = os.path.join(DASHBOARD_DIR, "mtd_cache.parquet")

# Kiem tra ket noi o mang X truoc khi chay
if not os.path.isdir(FOLDER):
    print("=" * 60)
    print("KHONG TRUY CAP DUOC O MANG X!")
    print(f"Duong dan: {FOLDER}")
    print("Kiem tra: 1) O X da ket noi chua?  2) Mo This PC xem co thay o X khong?")
    print("=" * 60)
    raise SystemExit

print("Doc file get_data tu o X...")

# Tu dong tim file Excel co chu "get_data" trong ten
INPUT_FILE = None
if os.path.isdir(FOLDER):
    for f in os.listdir(FOLDER):
        if f.lower().endswith((".xlsx", ".xls", ".xlsm")) and "get_data" in f.lower():
            INPUT_FILE = os.path.join(FOLDER, f)
            break

if INPUT_FILE is None:
    print(f"KHONG tim thay file Excel co chu 'get_data' trong: {FOLDER}")
    raise SystemExit

print(f"Da tim thay file: {os.path.basename(INPUT_FILE)}")

# Header that o dong 10 (index 9), data tu dong 11 (doc sheet dau tien)
raw = pd.read_excel(INPUT_FILE, sheet_name=0, header=9)

# Bo cac cot rong hoan toan
raw = raw.dropna(axis=1, how="all")

# ==================================================
# LAM SACH
# ==================================================
# Bo dong "Grand Total" o cuoi (khong co Item code) va dong rong
df = raw[raw["Item code"].notna()].copy()
df = df[df["MLA Name"].astype(str).str.strip().str.lower() != "grand total"]

# Doi ten cot ve chuan ngan gon cho trang doc
df = df.rename(columns={
    "correct channel name": "Channel",
    "CORRECT MLA":          "MLA",
    "Product Line desc":    "Product Line",
    "Family 2 Desc":        "Family 2",
    "Item code":            "Item code",
    "Comm. code":           "Comm code",
    "Item name":            "Item name",
    "Customer name":        "Customer",
    "Gross Sale":           "Gross",
    "NET SALE":             "Net",
    "REBATE":               "Rebate",
    "SGM":                  "SGM",
    "VOL":                  "VOL",
})

# Cac cot can giu
keep = ["Channel", "MLA", "Customer", "Product Line", "Family 2",
        "Item code", "Comm code", "Item name", "VOL",
        "Gross", "Rebate", "Net", "SGM"]
keep = [c for c in keep if c in df.columns]
df = df[keep].copy()

# Ep cac cot so sang numeric (o loi DIV/0 cua PRSC -> thanh NaN, khong sao)
num_cols = ["VOL", "Gross", "Rebate", "Net", "SGM"]
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# Cot text ep ve chuoi (tranh loi parquet)
for c in ["Channel", "MLA", "Customer", "Product Line", "Family 2",
          "Item code", "Comm code", "Item name"]:
    if c in df.columns:
        df[c] = df[c].astype(str).replace("nan", "")

# Ngay "as of" = thoi diem chay convert
as_of = pd.Timestamp.now()
df["As_of"] = as_of

# ==================================================
# KIEM TRA NHANH
# ==================================================
g, n, s = df["Gross"].sum(), df["Net"].sum(), df["SGM"].sum()
print(f"\nAs of: {as_of:%d-%b-%Y %H:%M}")
print(f"So dong chi tiet: {len(df)}")
print(f"So Channel : {df['Channel'].nunique()}")
print(f"So MLA     : {df['MLA'].nunique()}")
print(f"So Item    : {df['Item code'].nunique()}")
print(f"Tong Gross : {g:,.0f}")
print(f"Tong Net   : {n:,.0f}")
print(f"Deduction  : {g - n:,.0f}  ({(g-n)/g*100 if g else 0:.1f}%)")
print(f"Tong SGM   : {s:,.0f}  (SGM% = {s/n*100 if n else 0:.1f}%)")

# ==================================================
# LUU
# ==================================================
df.to_parquet(OUTPUT_FILE, index=False)
print(f"\n  -> Da luu: {OUTPUT_FILE}")

print("\nXONG!")
print("Buoc tiep: 1) Restart app  2) Upload mtd_cache.parquet len GitHub")
print("(Khong con can mtd_productline.parquet / mtd_family2.parquet)")
