"""
Convert 3 file Excel song tu SQL (ACT + SO + SQ) -> kam_cache.parquet
TU DONG hoa toan bo buoc mapping (thay cho Power Query lam tay truoc day).

Nguon (3 file tu SQL subscription, cap nhat moi 15 phut, nam trong o mang):
  - Sales detail with COGS.xlsx   (ACT - da xuat hoa don)
  - Sales Order Follow Up.xlsx     (SO  - don da dat, chua giao)
  - Sales Quotation Status.xlsx    (SQ  - bao gia)

Bang tra cuu (cung folder):
  - Customer map.xlsx        : Customer code -> MLA NAME + CHANNEL NAME
  - CMMF MAP.xlsx            : Item code -> Product Line
  - PRSC_KAM-VAT.xlsx        : Item code -> PRSC KAM (don gia von)
  - PRSC_FIN-VAT.xlsx        : Item code -> PRSC FIN
  - Mapping deduction rate.xlsx : DEALER NAME -> rate KAM/FIN (dò theo MLA)

Logic:
  1. Moi file: gom nhom theo Customer + Item + Product Line (nhu PivotTable)
  2. Map MLA/Channel (theo Customer), Product Line (theo Item), PRSC & deduction
  3. SO & SQ: chi giu dong Net > 0 ; ACT: lay het
  4. Ghep 3 file -> bo Channel = "SEB" (noi bo)
  5. Tinh Net = Gross*(1-rate), COGS = PRSC*Qty, SGM = Net - COGS
  6. Xuat kam_cache.parquet
"""
import pandas as pd
import os
import time
import zipfile
import xml.etree.ElementTree


def read_excel_retry(path, retries=3, wait=5, **kwargs):
    """Doc file Excel, tu dong thu lai neu file dang duoc SQL ghi do dang.
    Cac loi thuong gap khi file chua ghi xong: BadZipFile, EOFError, ParseError.
    Thu lai toi da 'retries' lan, moi lan cach 'wait' giay."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return pd.read_excel(path, **kwargs)
        except (zipfile.BadZipFile, EOFError,
                xml.etree.ElementTree.ParseError) as e:
            last_err = e
            if attempt < retries:
                print(f"    ! File dang ghi do ({os.path.basename(path)}), "
                      f"thu lai lan {attempt+1}/{retries} sau {wait}s...")
                time.sleep(wait)
            else:
                print(f"    ! File {os.path.basename(path)} van loi sau {retries} lan thu.")
    raise last_err

# ==================================================
# DUONG DAN
# ==================================================
FOLDER        = r"X:\Finance 2.Controlling\Monthly Reporting\2025\4. Monthly sale vs SGM report\auto data"
DED_FOLDER    = r"X:\Finance 2.Controlling\Dashboard"   # rieng file deduction rate
DASHBOARD_DIR = r"C:\AI_Dashboard"
OUTPUT_FILE   = os.path.join(DASHBOARD_DIR, "kam_cache.parquet")

# Ten file nguon (doi o day neu ten file thay doi)
F_ACT = "Sales detail with COGS.xlsx"
F_SO  = "Sales Order Follow Up.xlsx"
F_SQ  = "Sales Quotation Status.xlsx"
F_CUST = "Customer map.xlsx"
F_CMMF = "CMMF MAP.xlsx"
F_PRSC_KAM = "PRSC_KAM-VAT.xlsx"
F_PRSC_FIN = "PRSC_FIN-VAT.xlsx"
F_DED = "Mapping deduction rate.xlsx"

# Kiem tra ket noi o mang
if not os.path.isdir(FOLDER):
    print("=" * 60)
    print("KHONG TRUY CAP DUOC O MANG X!")
    print(f"Duong dan: {FOLDER}")
    print("Kiem tra: 1) O X da ket noi chua?  2) Mo This PC xem co thay o X khong?")
    print("=" * 60)
    raise SystemExit


def P(name):
    return os.path.join(FOLDER, name)


def clean_code(s):
    """Chuan hoa ma so: bo .0 o duoi, bo khoang trang."""
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def need(name):
    if not os.path.exists(P(name)):
        print(f"KHONG tim thay file: {name} trong {FOLDER}")
        raise SystemExit


# Duong dan day du cua file deduction rate (o folder rieng)
DED_PATH = os.path.join(DED_FOLDER, F_DED)

for fn in [F_ACT, F_SO, F_SQ, F_CUST, F_CMMF, F_PRSC_KAM, F_PRSC_FIN]:
    need(fn)

if not os.path.exists(DED_PATH):
    print(f"KHONG tim thay file deduction: {DED_PATH}")
    raise SystemExit

print("Doc cac bang tra cuu...")

# ==================================================
# BANG TRA CUU
# ==================================================
cust = read_excel_retry(P(F_CUST), header=0)
cust["K"] = clean_code(cust["Customer code"])
CUST_MLA = cust.drop_duplicates("K").set_index("K")["MLA NAME"]
CUST_CH  = cust.drop_duplicates("K").set_index("K")["CHANNEL NAME"]

cmmf = read_excel_retry(P(F_CMMF), header=0)
cmmf.columns = [str(c).strip() for c in cmmf.columns]
cmmf["K"] = clean_code(cmmf["Item Code"])
CMMF_PL = cmmf.drop_duplicates("K").set_index("K")["Product Line"]

pk = read_excel_retry(P(F_PRSC_KAM), sheet_name="PRSC_KAM", header=0)
pk["K"] = clean_code(pk["Item code"])
PRSC_K = pk.drop_duplicates("K").set_index("K")["PRSC -KAM"]

pf = read_excel_retry(P(F_PRSC_FIN), sheet_name="PRSC_FIN", header=0)
pf["K"] = clean_code(pf["Item code"])
PRSC_F = pf.drop_duplicates("K").set_index("K")["PRSC - FIN"]

ded = read_excel_retry(DED_PATH, sheet_name="MAPPING", header=1)
ded["K"] = ded["DEALER NAME"].astype(str).str.strip().str.upper()
DED_K = ded.drop_duplicates("K").set_index("K")["KAM"]
DED_F = ded.drop_duplicates("K").set_index("K")["FIN"]

# Bang tra Family 2 (Item code -> Family 2), lay tu mtd_cache.parquet neu co.
# mtd_cache co san cot Item code + Family 2. Dung de gan Family 2 cho tab By Family Level 2.
FAM2_MAP = None
_mtd_path = os.path.join(DASHBOARD_DIR, "mtd_cache.parquet")
if os.path.exists(_mtd_path):
    try:
        _m = pd.read_parquet(_mtd_path, columns=["Item code", "Family 2"])
        _m["K"] = clean_code(_m["Item code"])
        FAM2_MAP = _m.drop_duplicates("K").set_index("K")["Family 2"]
        print(f"  Doc bang tra Family 2 tu mtd_cache: {len(FAM2_MAP)} item")
    except Exception as e:
        print(f"  ! Khong doc duoc Family 2 tu mtd_cache: {e}")
else:
    print("  ! Chua co mtd_cache.parquet - Family 2 se de trong (chay convert_mtd.py truoc)")


# ==================================================
# HAM XU LY 1 FILE NGUON
# ==================================================
def build_source(fname, sheet, header, col, net_gt0, cancel_col=None):
    """Doc 1 file nguon, gom nhom, map, tra ve bang chuan.
    cancel_col: neu co, chi giu dong co gia tri = 'N' (bo CANCELED Y/C)."""
    df = read_excel_retry(P(fname), sheet_name=sheet, header=header)
    df.columns = [str(c).strip() for c in df.columns]

    # Bo dong Grand Total / dong tong / dong rong:
    # cac dong nay thieu Customer code hoac Item code (NaN/rong)
    cust_c, item_c = col["cust"], col["item"]
    before_gt = len(df)
    df = df[df[cust_c].notna() & df[item_c].notna()]
    df = df[df[cust_c].astype(str).str.strip() != ""]
    df = df[df[item_c].astype(str).str.strip() != ""]
    # Phong truong hop chu "grand total" nam trong cot ten
    for c in df.columns:
        if df[c].dtype == object:
            df = df[~df[c].astype(str).str.strip().str.lower().eq("grand total")]
    removed_gt = before_gt - len(df)
    if removed_gt:
        print(f"    {fname}: bo {removed_gt} dong Grand Total / rong")

    # Loc bo dong da huy (chi ap dung cho file co cot CANCELED, vd ACT)
    if cancel_col and cancel_col in df.columns:
        before = len(df)
        df = df[df[cancel_col].astype(str).str.strip().str.upper() == "N"]
        print(f"    {fname}: bo {before - len(df)} dong CANCELED (giu CANCELED = N)")

    tmp = pd.DataFrame({
        "Cust":  clean_code(df[col["cust"]]),
        "Item":  clean_code(df[col["item"]]),
        "Comm":  df[col["comm"]].astype(str).replace("nan", ""),
        "Name":  df[col["name"]].astype(str).replace("nan", ""),
        "Qty":   pd.to_numeric(df[col["qty"]], errors="coerce").fillna(0),
        "Gross": pd.to_numeric(df[col["gross"]], errors="coerce").fillna(0),
    })
    # Product Line map theo Item code
    tmp["PL"] = tmp["Item"].map(CMMF_PL)

    # Gom nhom theo Customer + Item + Product Line (nhu PivotTable)
    g = (tmp.groupby(["Cust", "Item", "PL"], observed=True, dropna=False)
         .agg(Qty=("Qty", "sum"), Gross=("Gross", "sum"),
              Comm=("Comm", "first"), Name=("Name", "first"))
         .reset_index())

    # Map MLA + Channel theo Customer
    g["MLA"]     = g["Cust"].map(CUST_MLA)
    g["Channel"] = g["Cust"].map(CUST_CH)

    # Deduction rate theo MLA (dò vao DEALER NAME)
    mkey = g["MLA"].astype(str).str.strip().str.upper()
    g["rate_KAM"] = mkey.map(DED_K).fillna(0)
    g["rate_FIN"] = mkey.map(DED_F).fillna(0)

    # PRSC theo Item code
    g["PRSC_KAM"] = g["Item"].map(PRSC_K).fillna(0)
    g["PRSC_FIN"] = g["Item"].map(PRSC_F).fillna(0)

    # Net KAM (dung de loc Net>0 cho SO/SQ)
    g["Net_KAM"] = g["Gross"] * (1 - g["rate_KAM"])
    if net_gt0:
        g = g[g["Net_KAM"] > 0]

    return g


print("Doc & xu ly 3 file nguon (ACT + SO + SQ)...")

ACT = build_source(
    F_ACT, "Sales detail with COGS", 3,
    dict(cust="Customer code", item="Item code", comm="Comm. code",
         name="Item name", qty="Quantity", gross="Line Totalafter All DC"),
    net_gt0=False, cancel_col="CANCELED")

SO = build_source(
    F_SO, "Sales Order Follow Up", 3,
    dict(cust="Customer Code", item="Item Code", comm="Commerical code",
         name="Item name", qty="SO Open Qty", gross="SO Actual Open Sum"),
    net_gt0=True)

SQ = build_source(
    F_SQ, "Sales Quotation Status", 2,
    dict(cust="Customer Code", item="Item Code", comm="Commerical code",
         name="Item name", qty="Open Qty", gross="Actual Open Sum"),
    net_gt0=True)

print(f"  ACT: {len(ACT):,} dong | SO: {len(SO):,} dong | SQ: {len(SQ):,} dong")

# ==================================================
# GHEP 3 NGUON + BO CHANNEL = SEB
# ==================================================
df = pd.concat([ACT, SO, SQ], ignore_index=True)

before = len(df)
df = df[df["Channel"].astype(str).str.strip().str.upper() != "SEB"]
df = df[df["MLA"].astype(str).str.strip().str.upper() != "SEB"]
print(f"  Bo Channel = SEB / MLA = SEB (noi bo): {before - len(df)} dong")

# ==================================================
# TINH TOAN CUOI
# ==================================================
df["Net_KAM"] = df["Gross"] * (1 - df["rate_KAM"])
df["Net_FIN"] = df["Gross"] * (1 - df["rate_FIN"])
df["COGS_KAM"] = df["PRSC_KAM"] * df["Qty"]
df["COGS_FIN"] = df["PRSC_FIN"] * df["Qty"]
df["SGM_KAM"] = df["Net_KAM"] - df["COGS_KAM"]
df["SGM_FIN"] = df["Net_FIN"] - df["COGS_FIN"]

# Doi ten cot ve chuan ma page_kam_mtd.py can
out = pd.DataFrame({
    "Channel":      df["Channel"].astype(str).replace("nan", ""),
    "MLA":          df["MLA"].astype(str).replace("nan", ""),
    "Customer":     df["Cust"].astype(str),
    "Product Line": df["PL"].astype(str).replace("nan", ""),
    "Item code":    df["Item"].astype(str),
    "Comm code":    df["Comm"].astype(str),
    "Item name":    df["Name"].astype(str),
    "Qty":          pd.to_numeric(df["Qty"], errors="coerce").fillna(0),
    "Gross":        pd.to_numeric(df["Gross"], errors="coerce").fillna(0),
    "Net_KAM":      df["Net_KAM"],
    "SGM_KAM":      df["SGM_KAM"],
    "Net_FIN":      df["Net_FIN"],
    "SGM_FIN":      df["SGM_FIN"],
})

# Family 2: map theo Item code; item nao chua co -> dung tam Product Line
if FAM2_MAP is not None:
    out["Family 2"] = clean_code(out["Item code"]).map(FAM2_MAP)
    # Thieu Family 2 -> dien tam bang Product Line
    miss = out["Family 2"].isna() | (out["Family 2"].astype(str).str.strip() == "")
    out.loc[miss, "Family 2"] = out.loc[miss, "Product Line"]
    out["Family 2"] = out["Family 2"].astype(str).replace("nan", "")
    n_fam_tam = int(miss.sum())
else:
    out["Family 2"] = out["Product Line"]  # fallback: chua co mtd_cache
    n_fam_tam = len(out)

as_of = pd.Timestamp.now()
out["As_of"] = as_of

# ==================================================
# KIEM TRA NHANH
# ==================================================
def pct(n, d): return n / d * 100 if d else 0

g = out["Gross"].sum()
print("\n" + "=" * 60)
print(f"As of: {as_of:%d-%b-%Y %H:%M}")
print(f"So dong chi tiet: {len(out):,}")
print(f"So Channel: {out['Channel'].nunique()} | MLA: {out['MLA'].nunique()} | Item: {out['Item code'].nunique()}")
print(f"Tong Gross : {g:,.0f}")
nk, sk = out["Net_KAM"].sum(), out["SGM_KAM"].sum()
nf, sf = out["Net_FIN"].sum(), out["SGM_FIN"].sum()
print(f"[KAM] Net {nk:,.0f} | SGM% {pct(sk, nk):.2f}%")
print(f"[FIN] Net {nf:,.0f} | SGM% {pct(sf, nf):.2f}%")

# Canh bao neu co dong khong map duoc
n_no_mla = (out["MLA"] == "").sum() + out["MLA"].isna().sum()
n_no_pl  = (out["Product Line"] == "").sum()
if n_no_mla:
    print(f"  ! Co {n_no_mla} dong khong map duoc MLA (kiem tra Customer map)")
if n_no_pl:
    print(f"  ! Co {n_no_pl} dong khong map duoc Product Line (kiem tra CMMF MAP)")
if FAM2_MAP is not None and n_fam_tam:
    print(f"  ! Co {n_fam_tam} dong Family 2 dung tam Product Line (item chua co trong mtd_cache)")

# ==================================================
# LUU
# ==================================================
out.to_parquet(OUTPUT_FILE, index=False)
print(f"\n  -> Da luu: {OUTPUT_FILE}")
print("\nXONG!")
print("Buoc tiep: 1) Restart app  2) git add/commit/push (neu muon cap nhat cloud)")
