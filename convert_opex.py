r"""
Convert file OPEX tracking (YTD.xlsx) -> opex_cache.parquet

Nguon: X:\Finance 2.Controlling\Dashboard\AI_OPEX_tracking\YTD.xlsx
  - Sheet "OPEX Tracking", header nam o dong 5 (index 4)
  - Cot gia tri: Amount
  - Nhieu Type: ACT_25, ACT_26, BUD_26, F5+7 (va 'X' la dong rong -> bo)

Xuat: opex_cache.parquet -> C:\AI_Dashboard
"""
import pandas as pd
import os

# ==================================================
# DUONG DAN
# ==================================================
FOLDER        = r"X:\Finance 2.Controlling\Dashboard\AI_OPEX_tracking"
SRC_FILE      = os.path.join(FOLDER, "YTD.xlsx")
DASHBOARD_DIR = r"C:\AI_Dashboard"
OUTPUT_FILE   = os.path.join(DASHBOARD_DIR, "opex_cache.parquet")
SHEET         = "OPEX Tracking"
HEADER_ROW    = 4   # header o dong thu 5 (index 4)

# Kiem tra ket noi
if not os.path.isdir(FOLDER):
    print("=" * 60)
    print("KHONG TRUY CAP DUOC O MANG X!")
    print(f"Duong dan: {FOLDER}")
    print("Kiem tra ket noi o X roi chay lai.")
    print("=" * 60)
    raise SystemExit

if not os.path.exists(SRC_FILE):
    print(f"KHONG tim thay file: {SRC_FILE}")
    raise SystemExit

print("Doc file OPEX...")
df = pd.read_excel(SRC_FILE, sheet_name=SHEET, header=HEADER_ROW)
df = df.dropna(axis=1, how="all")
df.columns = [str(c).strip() for c in df.columns]

# ==================================================
# LAM SACH
# ==================================================
# Bo dong khong co Type hoac Type = 'X' (dong rong)
df = df[df["Type"].notna()]
df = df[df["Type"].astype(str).str.strip().str.upper() != "X"]

# Amount ve so
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

# Chuan hoa Period: '2026 01' -> '2026-01' (thong nhat dinh dang)
df["Period"] = (df["Period"].astype(str).str.strip()
                .str.replace(" ", "-", regex=False))

# Tach nam + thang tu Period (de loc/sort de hon)
df["Year"] = df["Period"].str[:4]
df["Month"] = df["Period"].str[-2:]

# Chuan hoa cac cot phan loai ve string (tranh loi NaN khi filter)
dim_cols = ["Type", "Period", "LE", "Cost Center Code", "Cost Center Name",
            "PnL Line", "sub_PnL Line", "GPS Nature Lev 1", "NATURE NAME",
            "NATURE L2 NAME", "GPS L2", "Hier1_Nat", "G/L Account Name"]
for c in dim_cols:
    if c in df.columns:
        df[c] = df[c].astype(str).str.strip().replace({"nan": "", "None": ""})

# Ep TAT CA cot con lai (tru Amount, Year, Month) ve string.
# Ly do: nhieu cot (vd GPS Item) lan lon so va chu (730003 va 80062A)
# khien parquet bao loi kieu du lieu hon hop.
keep_numeric = {"Amount"}
for c in df.columns:
    if c not in keep_numeric:
        df[c] = df[c].astype(str).str.strip().replace({"nan": "", "None": "", "NaT": ""})
        # Bo hau to .0 o cac ma so (ME, Cost Center Code, LE...)
        df[c] = df[c].str.replace(r"\.0$", "", regex=True)

# ==================================================
# KIEM TRA NHANH
# ==================================================
print("=" * 60)
print(f"So dong: {len(df):,}")
print(f"Cac Type: {df['Type'].value_counts().to_dict()}")
print(f"Period: {df['Period'].min()} -> {df['Period'].max()}")
print(f"Tong Amount: {df['Amount'].sum():,.0f}")
print()
# Tong theo Type nam 2026
for t in ["ACT_26", "BUD_26", "F5+7"]:
    s = df[df["Type"] == t]["Amount"].sum()
    print(f"  {t:<8}: {s:,.0f}")

# ==================================================
# LUU
# ==================================================
df.to_parquet(OUTPUT_FILE, index=False)
print(f"\n  -> Da luu: {OUTPUT_FILE}")
print("\nXONG! Buoc tiep: restart app / git push (neu muon cap nhat cloud)")
