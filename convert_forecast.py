"""
Convert cac file Excel Forecast (Sales & Standard COS Preview) -> forecast_cache.parquet

Cach dung:
  1. Bo cac file forecast vao folder tren o X, dat ten file = ten vong forecast:
       F4+8.xlsx
       F5+7.xlsx
       F7+5.xlsx
     (Ten file se thanh ten vong forecast hien trong dashboard)
  2. Chay: python convert_forecast.py

File Excel dang pivot ngang:
  - Dong 1 (index 0): ten thang (Jan.26, Feb.26, ...)
  - Dong 2 (index 1): loai so (Sales / COS / SGM%)
  - Cot 1 (index 0) : ten Family Level 2, xen ke dong "-  Product Line : XXX" va "Total XXX"

Ket qua: bang phang co cac cot
  Forecast | Product Line | Family Level 2 | MONTH | NS_FC | COS_FC | SGM%_FC | SGM_FC
"""
import pandas as pd
import os
import re

FOLDER        = r"X:\Finance 2.Controlling\Dashboard\AI_Forecast_rawdata"
DASHBOARD_DIR = r"C:\AI_Dashboard"
OUTPUT_FILE   = os.path.join(DASHBOARD_DIR, "forecast_cache.parquet")

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Kiem tra ket noi o mang X
if not os.path.isdir(FOLDER):
    print("=" * 60)
    print("KHONG TRUY CAP DUOC FOLDER FORECAST!")
    print(f"Duong dan: {FOLDER}")
    print("Kiem tra: 1) O X da ket noi chua?  2) Folder da tao chua?")
    print("=" * 60)
    raise SystemExit

print("Doc cac file Forecast tu o X...")

excel_files = [f for f in os.listdir(FOLDER)
               if f.lower().endswith((".xlsx", ".xls", ".xlsm")) and not f.startswith("~$")]

if not excel_files:
    print(f"KHONG tim thay file Excel nao trong: {FOLDER}")
    raise SystemExit

print(f"Tim thay {len(excel_files)} file:")
for f in excel_files:
    print(f"  - {f}")


def parse_forecast_file(path, fc_name):
    """Boc tach 1 file forecast dang pivot -> bang phang."""
    raw = pd.read_excel(path, sheet_name=0, header=None)

    months_row = raw.iloc[0]
    kind_row   = raw.iloc[1]

    # Xac dinh vi tri cot cho tung thang
    col_map = {}
    for c in range(raw.shape[1]):
        m, k = months_row[c], kind_row[c]
        if pd.isna(m) or pd.isna(k):
            continue
        m3 = str(m).strip()[:3]
        k = str(k).strip()
        if m3 in MONTH_ORDER and k in ("Sales", "COS", "SGM%"):
            col_map.setdefault(m3, {})[k] = c

    if not col_map:
        print(f"    ! Khong doc duoc cot thang trong {fc_name}, bo qua file nay.")
        return pd.DataFrame()

    rows = []
    current_pl = ""

    for i in range(2, raw.shape[0]):
        label = raw.iat[i, 0]
        if pd.isna(label):
            continue
        label = str(label).strip()

        # Dong phan nhom Product Line
        m = re.match(r"^-\s*Product Line\s*:\s*(.+)$", label)
        if m:
            current_pl = m.group(1).strip()
            continue

        # Bo qua dong tong va grand total
        if label.lower().startswith("total") or label.lower().startswith("- grand total"):
            continue
        if label.upper() == "TOTAL":
            continue

        # Dong du lieu Family Level 2
        for mth, kinds in col_map.items():
            ns  = raw.iat[i, kinds["Sales"]] if "Sales" in kinds else None
            cos = raw.iat[i, kinds["COS"]]   if "COS"   in kinds else None
            sgm_pct = raw.iat[i, kinds["SGM%"]] if "SGM%" in kinds else None

            ns  = pd.to_numeric(ns, errors="coerce")
            cos = pd.to_numeric(cos, errors="coerce")
            sgm_pct = pd.to_numeric(sgm_pct, errors="coerce")

            # Bo dong rong hoan toan
            if pd.isna(ns) and pd.isna(cos):
                continue

            ns  = 0.0 if pd.isna(ns)  else float(ns)
            cos = 0.0 if pd.isna(cos) else float(cos)

            # SGM tien = Sales + COS  (COS trong file la so am)
            sgm_amt = ns + cos

            # SGM% trong file la dang 45.02 (khong phai 0.4502)
            if pd.isna(sgm_pct):
                sgm_pct = (sgm_amt / ns * 100) if ns else 0.0
            else:
                sgm_pct = float(sgm_pct)

            rows.append({
                "Forecast":       fc_name,
                "Product Line":   current_pl,
                "Family Level 2": label,
                "MONTH":          mth,
                "NS_FC":          ns,
                "COS_FC":         cos,
                "SGM_FC":         sgm_amt,
                "SGM%_FC":        sgm_pct,
            })

    return pd.DataFrame(rows)


all_dfs = []
for f in excel_files:
    fc_name = os.path.splitext(f)[0].strip()   # Ten file = ten vong forecast
    print(f"\nDang doc {f}  (vong: {fc_name})...")
    d = parse_forecast_file(os.path.join(FOLDER, f), fc_name)
    if not d.empty:
        print(f"    -> {len(d):,} dong, {d['Family Level 2'].nunique()} Family, "
              f"{d['MONTH'].nunique()} thang")
        all_dfs.append(d)

if not all_dfs:
    print("\nKHONG boc tach duoc du lieu nao. Kiem tra lai dinh dang file.")
    raise SystemExit

df = pd.concat(all_dfs, ignore_index=True)

# Sap xep thang theo dung thu tu
df["MONTH"] = pd.Categorical(df["MONTH"], categories=MONTH_ORDER, ordered=True)
df = df.sort_values(["Forecast", "MONTH", "Product Line", "Family Level 2"])
df["MONTH"] = df["MONTH"].astype(str)

# Ep cot text
for c in ["Forecast", "Product Line", "Family Level 2", "MONTH"]:
    df[c] = df[c].astype(str)

as_of = pd.Timestamp.now()
df["As_of"] = as_of

# ==================================================
# KIEM TRA NHANH
# ==================================================
print("\n" + "=" * 60)
print(f"As of: {as_of:%d-%b-%Y %H:%M}")
print(f"Tong so dong    : {len(df):,}")
print(f"So vong forecast: {df['Forecast'].nunique()}  ->  {sorted(df['Forecast'].unique())}")
print(f"So Product Line : {df['Product Line'].nunique()}")
print(f"So Family Lv 2  : {df['Family Level 2'].nunique()}")

print("\nTong Net Sales theo tung vong forecast (ca nam):")
for fc, g in df.groupby("Forecast"):
    ns  = g["NS_FC"].sum()
    sgm = g["SGM_FC"].sum()
    pct = sgm / ns * 100 if ns else 0
    print(f"  {fc:<10} NS {ns:>18,.0f} | SGM {sgm:>16,.0f} | SGM% {pct:5.2f}%")

# ==================================================
# LUU
# ==================================================
df.to_parquet(OUTPUT_FILE, index=False)
print(f"\n  -> Da luu: {OUTPUT_FILE}")

size_kb = os.path.getsize(OUTPUT_FILE) / 1024
print(f"\nXONG! Kich thuoc: {size_kb:.0f} KB")
print("Buoc tiep: 1) Restart app  2) git add/commit/push de cap nhat cloud")
