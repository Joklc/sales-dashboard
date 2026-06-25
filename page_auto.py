"""
page_auto.py - Auto Dashboard
Doc thang tu o X:, bam Refresh la cap nhat, khong can convert file.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import os
from datetime import datetime

# ── Plotly theme (giống KAM MTD) ──────────────────────────────
if "seb_dark" not in pio.templates:
    pio.templates["seb_dark"] = go.layout.Template(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#0f172a", size=12),
            xaxis=dict(gridcolor="#cdd9e8", zerolinecolor="#cdd9e8"),
            yaxis=dict(gridcolor="#cdd9e8", zerolinecolor="#cdd9e8"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            colorway=["#3b82f6","#9ca3af","#f59e0b","#22d3ee","#a78bfa","#16a34a"],
        )
    )
pio.templates.default = "seb_dark"

# ── Config ────────────────────────────────────────────────────
# Dung o X: (da map san tren may nay). Neu chay may khac chua map X:,
# doi lai thanh duong dan day du \\hcv01it\AFV\Department\...
DATA_DIR = r"X:\Monthly Reporting\2025\4. Monthly sale vs SGM report\auto data"

def fp(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

CLR = {
    "blue":   "#3b82f6",
    "cyan":   "#22d3ee",
    "amber":  "#f59e0b",
    "purple": "#a78bfa",
    "green":  "#16a34a",
    "red":    "#dc2626",
    "gray":   "#9ca3af",
}

def safe_div(num, den):
    return num / den if den and den != 0 else 0

# ── CSS (giống KAM MTD) ───────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, #1e40af 0%, #1d4ed8 100%);
        border: 1px solid #1e3a8a;
        border-left: 4px solid #93c5fd;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 2px 6px rgba(30,64,175,0.25);
        height: 120px;
        display: flex; flex-direction: column; justify-content: flex-start;
    }
    [data-testid="stMetricDelta"] { font-size: 12px !important; margin-top: auto !important; }
    [data-testid="stMetricValue"] { font-size: 20px !important; font-weight: 700 !important; color: #ffffff !important; }
    [data-testid="stMetric"] label { font-size: 11px !important; font-weight: 600 !important; color: #bfdbfe !important; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# ── Data loading ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_all():
    """
    Đọc và merge tất cả file từ ổ X:.
    Trả về DataFrame đã tính sẵn Gross Sale, Net Sale, SGM FIN, SGM KAM, Deduction Rate.
    """
    # 1. Sales detail with COGS (header ở dòng 4, index=3)
    df = pd.read_excel(fp("Sales detail with COGS.xlsx"), header=3)
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        "Item code":     "Item_code",
        "Customer code": "Customer_code",
    })

    # 2. CMMF MAP: Item_code → Product Line & Family L2
    cmmf = pd.read_excel(fp("CMMF MAP.xlsx"))
    cmmf.columns = cmmf.columns.str.strip()
    _fl2 = next((c for c in cmmf.columns if "l2" in c.lower()), None)
    _cmmf_rename = {"Item Code": "Item_code", "Product Line": "CMMF_PL"}
    if _fl2:
        _cmmf_rename[_fl2] = "Family_L2"
    _keep = ["Item_code", "CMMF_PL"] + (["Family_L2"] if _fl2 else [])
    cmmf = cmmf.rename(columns=_cmmf_rename)[_keep].drop_duplicates("Item_code")

    # 3. Customer map: Customer_code → MLA, Channel chuẩn
    cust = pd.read_excel(fp("Customer map.xlsx"))
    cust.columns = cust.columns.str.strip()
    cust = (cust.rename(columns={
                "Customer code": "Customer_code",
                "MLA NAME":      "Map_MLA",
                "CHANNEL NAME":  "Map_Channel",
            }).drop_duplicates("Customer_code"))

    # 4. PRSC FIN: giá vốn Finance (per unit)
    pf = pd.read_excel(fp("PRSC_FIN-VAT.xlsx"))
    pf.columns = pf.columns.str.strip()
    pf = (pf.rename(columns={"Item code": "Item_code", "PRSC - FIN": "PRSC_FIN"})
            [["Item_code", "PRSC_FIN"]]
            .drop_duplicates("Item_code"))

    # 5. PRSC KAM: giá vốn theo góc nhìn Sales/KAM (per unit)
    pk = pd.read_excel(fp("PRSC_KAM-VAT.xlsx"))
    pk.columns = pk.columns.str.strip()
    pk = (pk.rename(columns={"Item code": "Item_code", "PRSC -KAM": "PRSC_KAM"})
            [["Item_code", "PRSC_KAM"]]
            .drop_duplicates("Item_code"))

    # Loại trừ SEB nội bộ và FOC (hàng biếu tặng, không tính doanh số)
    df = df[
        (df["Customer Group"].str.upper() != "SEB") &
        (df["FOC"].astype(str).str.upper() == "N")
    ]

    # Merge tất cả vào Sales detail
    df = (df
          .merge(cmmf, on="Item_code", how="left")
          .merge(cust,  on="Customer_code", how="left")
          .merge(pf,    on="Item_code", how="left")
          .merge(pk,    on="Item_code", how="left"))

    # 6. MAPPING DEDUCT: deduction rate cố định theo MLA (từ file chuẩn)
    mp = pd.read_excel(fp("MAPPING_DEDUCT.xlsx"))
    mp.columns = mp.columns.str.strip()
    mp["MLA_NAME"] = mp["MLA_NAME"].astype(str).str.strip().str.upper()
    mp = mp.drop_duplicates("MLA_NAME")

    # Normalize dimension: ưu tiên map file, fallback về cột SAP
    df["MLA"]       = df["Map_MLA"].fillna(df.get("MLA Name", "")).astype(str).str.strip()
    df["Channel"]   = df["Map_Channel"].fillna(df.get("Channel Name", ""))
    df["Prod_Line"] = df["CMMF_PL"].fillna(df.get("Product line", ""))

    # Loại các mã Product Line ngắn (1 ký tự: S, G, R, B, H, Z...) — item không có trong CMMF MAP
    df = df[df["Prod_Line"].astype(str).str.len() > 2]

    if "Family_L2" not in df.columns:
        df["Family_L2"] = "N/A"
    else:
        df["Family_L2"] = df["Family_L2"].fillna("N/A").astype(str).str.strip()

    # Join deduction rate theo MLA
    df["MLA_KEY"] = df["MLA"].str.upper()
    df = df.merge(mp[["MLA_NAME","KAM_DEDUCT","FIN_DEDUCT"]],
                  left_on="MLA_KEY", right_on="MLA_NAME", how="left")
    df["FIN_DEDUCT"] = df["FIN_DEDUCT"].fillna(0)
    df["KAM_DEDUCT"] = df["KAM_DEDUCT"].fillna(0)

    # ── Tính toán tài chính (đúng theo file chuẩn) ───────────
    qty = df["Quantity"].fillna(0)

    # Gross Sale = Line Total after All DC (doanh thu trên hóa đơn sau DC invoice)
    df["Gross_Sale"] = df["Line Totalafter All DC"].fillna(0)

    # Net Sale = Gross x (1 - Deduction Rate từ MAPPING)
    df["Net_Sale_FIN"] = df["Gross_Sale"] * (1 - df["FIN_DEDUCT"])
    df["Net_Sale_KAM"] = df["Gross_Sale"] * (1 - df["KAM_DEDUCT"])

    # COGS = PRSC (giá vốn/unit) × Số lượng
    df["COGS_FIN"] = df["PRSC_FIN"].fillna(0) * qty
    df["COGS_KAM"] = df["PRSC_KAM"].fillna(0) * qty

    # SGM% = (Net Sale - COGS) / Net Sale
    df["SGM_pct_FIN"] = df.apply(
        lambda r: safe_div(r["Net_Sale_FIN"] - r["COGS_FIN"], r["Net_Sale_FIN"]) * 100, axis=1)
    df["SGM_pct_KAM"] = df.apply(
        lambda r: safe_div(r["Net_Sale_KAM"] - r["COGS_KAM"], r["Net_Sale_KAM"]) * 100, axis=1)

    # SGM absolute
    df["SGM_FIN"] = df["Net_Sale_FIN"] - df["COGS_FIN"]
    df["SGM_KAM"] = df["Net_Sale_KAM"] - df["COGS_KAM"]

    # Deduction amount & rate (for display)
    df["Deduction_FIN"]     = df["Gross_Sale"] * df["FIN_DEDUCT"]
    df["Deduction_KAM"]     = df["Gross_Sale"] * df["KAM_DEDUCT"]
    df["Ded_Rate_pct_FIN"]  = df["FIN_DEDUCT"] * 100
    df["Ded_Rate_pct_KAM"]  = df["KAM_DEDUCT"] * 100

    # Date
    df["Doc_date"]  = pd.to_datetime(df["Doc date"], errors="coerce")
    df["Month"]     = df["Doc_date"].dt.strftime("%b")
    df["Month_num"] = df["Doc_date"].dt.month

    return df


@st.cache_data(show_spinner=False)
def load_pipeline():
    """Đọc Sales Order Follow Up và Quotation, loại trừ dòng Gross Sale = 0."""
    so = pd.read_excel(fp("Sales Order Follow Up.xlsx"), header=3)
    so.columns = so.columns.str.strip()
    so["Gross_Sale"] = so["SO Actual Open Sum"].fillna(0)
    so = so[so["Gross_Sale"] > 0].copy()

    sq = pd.read_excel(fp("Sales Quotation Status.xlsx"), header=2)
    sq.columns = sq.columns.str.strip()
    sq["Gross_Sale"] = sq["Actual Open Sum"].fillna(0)
    sq = sq[sq["Gross_Sale"] > 0].copy()

    return so, sq

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.markdown("## ⚡ Auto Dashboard")

# FIN vs KAM toggle
view = st.sidebar.radio(
    "SGM View",
    options=["FIN — Finance", "KAM — Sales"],
    help="FIN: dùng PRSC_FIN làm giá vốn | KAM: dùng PRSC_KAM",
)
is_fin       = view.startswith("FIN")
net_col      = "Net_Sale_FIN"    if is_fin else "Net_Sale_KAM"
cogs_col     = "COGS_FIN"        if is_fin else "COGS_KAM"
sgm_col      = "SGM_FIN"         if is_fin else "SGM_KAM"
sgm_pct_col  = "SGM_pct_FIN"     if is_fin else "SGM_pct_KAM"
deduct_col   = "Deduction_FIN"   if is_fin else "Deduction_KAM"
ded_rate_col = "Ded_Rate_pct_FIN" if is_fin else "Ded_Rate_pct_KAM"
view_label   = "FIN" if is_fin else "KAM"

st.sidebar.markdown("---")

# Nút Refresh — clear cache rồi rerun
if st.sidebar.button("🔄  Refresh Data từ ổ X:", use_container_width=True, type="primary"):
    load_all.clear()
    load_pipeline.clear()
    st.rerun()

st.sidebar.markdown("---")

# ── Load data ─────────────────────────────────────────────────
with st.spinner("📥 Đang đọc file từ ổ X:\\..."):
    try:
        if not os.path.isdir(DATA_DIR):
            st.error(
                "❌ Không vào được folder dữ liệu:\n\n"
                f"`{DATA_DIR}`\n\n"
                "Kiểm tra: (1) đã kết nối mạng công ty chưa, "
                "(2) đường dẫn folder có đúng không. "
                "Mở File Explorer, dán đường dẫn trên vào thanh địa chỉ để thử."
            )
            st.stop()
        df       = load_all()
        df_so, df_sq = load_pipeline()
        load_ts  = datetime.now().strftime("%H:%M  %d/%m/%Y")
    except FileNotFoundError as e:
        st.error(f"❌ Không tìm thấy file: {e}\n\nKiểm tra ổ X: đã được kết nối chưa.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Lỗi đọc file: {e}")
        st.stop()

# ── Filters ───────────────────────────────────────────────────
avail_months = [m for m in MONTH_ORDER if m in df["Month"].dropna().unique()]

sel_month   = st.sidebar.selectbox("Month",        ["All"] + avail_months)
sel_channel = st.sidebar.selectbox("Channel",      ["All"] + sorted(df["Channel"].dropna().astype(str).unique()))
sel_mla     = st.sidebar.selectbox("MLA",          ["All"] + sorted(df["MLA"].dropna().astype(str).unique()))
sel_pl      = st.sidebar.selectbox("Product Line", ["All"] + sorted(df["Prod_Line"].dropna().astype(str).unique()))

mask = pd.Series(True, index=df.index)
if sel_month   != "All": mask &= df["Month"]     == sel_month
if sel_channel != "All": mask &= df["Channel"]   == sel_channel
if sel_mla     != "All": mask &= df["MLA"]       == sel_mla
if sel_pl      != "All": mask &= df["Prod_Line"] == sel_pl
dff = df[mask]

# ── Header ────────────────────────────────────────────────────
period = sel_month if sel_month != "All" else "YTD"
st.title(f"⚡ Auto Dashboard — {period}")
st.caption(
    f"Dữ liệu: {load_ts}  •  {len(dff):,} dòng  •  "
    f"SGM View: **{view_label}**  •  "
    f"Bấm **Refresh** trên sidebar để cập nhật file mới nhất"
)
st.markdown("---")

# ── KPI Cards ─────────────────────────────────────────────────
gross  = dff["Gross_Sale"].sum()
net    = dff[net_col].sum()
deduct = dff[deduct_col].sum()
cogs   = dff[cogs_col].sum()
sgm    = dff[sgm_col].sum()

ded_pct = safe_div(deduct, gross) * 100
sgm_pct = safe_div(sgm, net) * 100

st.subheader(f"📊 Summary — {view_label} view")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Gross Sales",          f"{gross:,.0f}")
c2.metric(f"Net Sales ({view_label})",  f"{net:,.0f}")
c3.metric("Sale Deduction",       f"{deduct:,.0f}")
c4.metric("Deduction %",          f"{ded_pct:.1f}%")
c5.metric(f"SGM ({view_label})",  f"{sgm:,.0f}")
c6.metric(f"SGM % ({view_label})", f"{sgm_pct:.1f}%")

c7, c8, c9, c10 = st.columns(4)
c7.metric("No. of MLA",       f"{dff['MLA'].nunique()}")
c8.metric("No. of Items",     f"{dff['Item_code'].nunique()}")
c9.metric("No. of Customers", f"{dff['Customer_code'].nunique()}")
c10.metric("Total Qty",       f"{dff['Quantity'].sum():,.0f}")

# ── Sales Contribution ────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Sales Contribution")

def render_contribution(df_in, dim_col, dim_label):
    grp = (
        df_in.groupby(dim_col, as_index=False, observed=True)
             .agg(Net_Sale=(net_col, "sum"), SGM=(sgm_col, "sum"))
             .sort_values("Net_Sale", ascending=False)
    )
    grp = grp[grp[dim_col].astype(str).str.strip() != ""]
    total_net = grp["Net_Sale"].sum()
    grp["Contrib%"] = grp["Net_Sale"].apply(lambda v: safe_div(v, total_net) * 100)
    grp["SGM%"]     = grp.apply(lambda r: safe_div(r["SGM"], r["Net_Sale"]) * 100, axis=1)
    grp = grp.rename(columns={dim_col: dim_label})

    col_chart, col_table = st.columns([3, 2])
    with col_chart:
        grp_asc = grp.sort_values("Net_Sale")
        sgm_max = max(grp_asc["SGM%"].max() * 1.4, 10)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=grp_asc[dim_label],
            x=grp_asc["Net_Sale"],
            orientation="h",
            name="Net Sale",
            marker_color=CLR["blue"],
            text=grp_asc["Contrib%"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            xaxis="x",
        ))
        fig.add_trace(go.Scatter(
            y=grp_asc[dim_label],
            x=grp_asc["SGM%"],
            mode="markers+text",
            name=f"SGM% ({view_label})",
            marker=dict(size=11, color=CLR["amber"], symbol="diamond"),
            text=grp_asc["SGM%"].round(1).astype(str) + "%",
            textposition="middle right",
            xaxis="x2",
        ))
        fig.update_layout(
            xaxis=dict(title="Net Sale", showgrid=True),
            xaxis2=dict(
                title="SGM%", overlaying="x", side="top",
                ticksuffix="%", showgrid=False,
                range=[0, sgm_max],
            ),
            height=max(340, len(grp) * 44),
            margin=dict(t=40, b=10, l=10, r=120),
            template="seb_dark",
            legend=dict(orientation="h", y=-0.10),
        )
        st.plotly_chart(fig, use_container_width=True)
    with col_table:
        st.dataframe(
            grp[[dim_label, "Net_Sale", "Contrib%", "SGM%"]]
            .style.format({"Net_Sale": "{:,.0f}", "Contrib%": "{:.1f}%", "SGM%": "{:.1f}%"}),
            use_container_width=True,
            hide_index=True,
            height=max(340, len(grp) * 38),
        )

tab_cont_ch, tab_cont_mla, tab_cont_pl = st.tabs(
    ["By Channel", "By MLA", "By Product Line"]
)
with tab_cont_ch:
    render_contribution(dff, "Channel",   "Channel")
with tab_cont_mla:
    render_contribution(dff, "MLA",       "MLA")
with tab_cont_pl:
    grp_pl = (
        dff.groupby("Prod_Line", as_index=False, observed=True)
           .agg(Net_Sale=(net_col, "sum"), SGM=(sgm_col, "sum"))
           .sort_values("Net_Sale", ascending=False)
    )
    grp_pl = grp_pl[grp_pl["Prod_Line"].astype(str).str.strip() != ""]
    total_pl = grp_pl["Net_Sale"].sum()
    grp_pl["Contrib%"] = grp_pl["Net_Sale"].apply(lambda v: safe_div(v, total_pl) * 100)
    grp_pl["SGM%"]     = grp_pl.apply(lambda r: safe_div(r["SGM"], r["Net_Sale"]) * 100, axis=1)

    col_donut, col_tbl = st.columns([3, 2])
    with col_donut:
        DONUT_COLORS = ["#3b82f6","#22d3ee","#a78bfa","#f59e0b",
                        "#16a34a","#ef4444","#8b5cf6","#14b8a6",
                        "#f97316","#9ca3af","#ec4899","#84cc16"]
        fig_donut = go.Figure(go.Pie(
            labels=grp_pl["Prod_Line"],
            values=grp_pl["Net_Sale"],
            hole=0.52,
            textinfo="label+percent",
            textposition="outside",
            marker=dict(colors=DONUT_COLORS[:len(grp_pl)],
                        line=dict(color="#ffffff", width=2)),
            hovertemplate="<b>%{label}</b><br>Net Sale: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        ))
        fig_donut.update_layout(
            height=460,
            margin=dict(t=30, b=30, l=10, r=10),
            template="seb_dark",
            showlegend=True,
            legend=dict(orientation="v", x=1.02, y=0.5),
            annotations=[dict(
                text=f"Net Sale<br><b>{total_pl/1e9:.1f}B</b>",
                x=0.5, y=0.5, font_size=14, showarrow=False,
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    with col_tbl:
        st.dataframe(
            grp_pl[["Prod_Line", "Net_Sale", "Contrib%", "SGM%"]]
            .rename(columns={"Prod_Line": "Product Line"})
            .style.format({"Net_Sale": "{:,.0f}", "Contrib%": "{:.1f}%", "SGM%": "{:.1f}%"}),
            use_container_width=True,
            hide_index=True,
            height=460,
        )

# ── Breakdown ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("🔍 Breakdown Analysis")

tab_ch, tab_mla, tab_pl = st.tabs(["By Channel", "By MLA", "By Product Line"])


def render_breakdown(df_in: pd.DataFrame, dim_col: str, dim_label: str):
    grp = (
        df_in.groupby(dim_col, as_index=False, observed=True)
             .agg(Gross_Sale=("Gross_Sale","sum"),
                  Net_Sale=(net_col,"sum"),
                  Deduction=(deduct_col,"sum"),
                  SGM=(sgm_col,"sum"))
             .sort_values("Gross_Sale", ascending=False)
             .head(15)
    )
    grp["Ded_Rate%"] = grp.apply(
        lambda r: safe_div(r["Deduction"], r["Gross_Sale"]) * 100, axis=1)
    grp["SGM%"] = grp.apply(
        lambda r: safe_div(r["SGM"], r["Net_Sale"]) * 100, axis=1)
    grp = grp.rename(columns={dim_col: dim_label})

    col_chart, col_table = st.columns([3, 2])
    with col_chart:
        grp_asc = grp.sort_values("Gross_Sale")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=grp_asc[dim_label], x=grp_asc["Gross_Sale"],
            name="Gross Sale", orientation="h", marker_color=CLR["blue"]))
        fig.add_trace(go.Bar(
            y=grp_asc[dim_label], x=grp_asc["Net_Sale"],
            name="Net Sale", orientation="h", marker_color=CLR["cyan"]))
        fig.update_layout(
            barmode="group",
            height=max(320, len(grp) * 40),
            margin=dict(t=10, b=10, l=10, r=10),
            template="seb_dark",
            legend=dict(orientation="h", y=-0.12),
        )
        st.plotly_chart(fig, use_container_width=True)
    with col_table:
        st.dataframe(
            grp[[dim_label, "Gross_Sale", "Net_Sale", "Ded_Rate%", "SGM%"]]
            .style.format({
                "Gross_Sale": "{:,.0f}",
                "Net_Sale":   "{:,.0f}",
                "Ded_Rate%":  "{:.1f}%",
                "SGM%":       "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
            height=max(320, len(grp) * 38),
        )


with tab_ch:
    render_breakdown(dff, "Channel",   "Channel")
with tab_mla:
    render_breakdown(dff, "MLA",       "MLA")
with tab_pl:
    render_breakdown(dff, "Prod_Line", "Product Line")

# ── Pipeline ──────────────────────────────────────────────────
st.markdown("---")
st.subheader("🚀 Sales Pipeline")

tab_so, tab_sq = st.tabs(["Open Sales Orders", "Open Quotations"])

with tab_so:
    so_open = df_so[df_so["Gross_Sale"] > 0].copy()
    so_total = so_open["Gross_Sale"].sum()
    n_so     = len(so_open)

    pm1, pm2, pm3 = st.columns(3)
    pm1.metric("Open SO — Gross Sale",  f"{so_total:,.0f}")
    pm2.metric("Số lệnh SO",            f"{n_so:,}")
    pm3.metric("TB / lệnh",             f"{safe_div(so_total, n_so):,.0f}")

    if "Channel Name" in so_open.columns:
        so_ch = (so_open.groupby("Channel Name", as_index=False)["Gross_Sale"]
                 .sum().sort_values("Gross_Sale", ascending=False))
        fig_so = go.Figure(go.Bar(
            x=so_ch["Channel Name"], y=so_ch["Gross_Sale"],
            marker_color=CLR["blue"],
            text=so_ch["Gross_Sale"].apply(lambda v: f"{v:,.0f}"),
            textposition="outside",
        ))
        fig_so.update_layout(
            height=300, template="seb_dark",
            margin=dict(t=10, b=10), showlegend=False,
        )
        st.plotly_chart(fig_so, use_container_width=True)

    show_so = [c for c in [
        "SO num", "Customer Name", "Item Code", "Item name",
        "SO Quantity", "SO Actual Open Sum", "Expected Delivery Date",
        "Channel Name", "SO Status",
    ] if c in so_open.columns]
    st.dataframe(so_open[show_so].head(500), use_container_width=True, hide_index=True)

with tab_sq:
    sq_total = df_sq["Gross_Sale"].sum()
    n_sq     = len(df_sq)

    qm1, qm2, qm3 = st.columns(3)
    qm1.metric("Open Quotation — Gross Sale", f"{sq_total:,.0f}")
    qm2.metric("Số báo giá",                  f"{n_sq:,}")
    qm3.metric("TB / báo giá",                f"{safe_div(sq_total, n_sq):,.0f}")

    if "Channel name" in df_sq.columns:
        sq_ch = (df_sq.groupby("Channel name", as_index=False)["Gross_Sale"]
                 .sum().sort_values("Gross_Sale", ascending=False))
        fig_sq = go.Figure(go.Bar(
            x=sq_ch["Channel name"], y=sq_ch["Gross_Sale"],
            marker_color=CLR["purple"],
            text=sq_ch["Gross_Sale"].apply(lambda v: f"{v:,.0f}"),
            textposition="outside",
        ))
        fig_sq.update_layout(
            height=300, template="seb_dark",
            margin=dict(t=10, b=10), showlegend=False,
        )
        st.plotly_chart(fig_sq, use_container_width=True)

    show_sq = [c for c in [
        "Quotation num", "Customer Name", "Item name", "Quantity",
        "Price (AfterDiscount)", "Actual Open Sum",
        "Status", "Valid Until", "Channel name",
    ] if c in df_sq.columns]
    st.dataframe(df_sq[show_sq].head(200), use_container_width=True, hide_index=True)

# ── Detail table ──────────────────────────────────────────────
with st.expander(f"📋 Detail Data ({len(dff):,} dòng — hiển thị tối đa 1000)", expanded=False):
    detail_cols = [c for c in [
        "Doc_date", "Month", "Channel", "MLA",
        "Customer name", "Prod_Line",
        "Item_code", "Item name", "Quantity",
        "Gross_Sale", deduct_col, ded_rate_col, net_col,
        cogs_col, sgm_col,
    ] if c in dff.columns]

    display = (dff[detail_cols]
               .rename(columns={
                   net_col:      f"Net_Sale_{view_label}",
                   deduct_col:   f"Deduction_{view_label}",
                   ded_rate_col: "Ded_Rate%",
                   cogs_col:     f"COGS_{view_label}",
                   sgm_col:      f"SGM_{view_label}",
               })
               .head(1000))
    st.dataframe(
        display.style.format({
            "Gross_Sale":               "{:,.0f}",
            f"Net_Sale_{view_label}":   "{:,.0f}",
            f"Deduction_{view_label}":  "{:,.0f}",
            "Ded_Rate%":                "{:.1f}%",
            f"COGS_{view_label}":       "{:,.0f}",
            f"SGM_{view_label}":        "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
    if len(dff) > 1000:
        st.caption("💡 Chỉ hiển thị 1000 dòng đầu. Dùng filter để thu hẹp phạm vi.")
