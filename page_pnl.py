import streamlit as st
import pandas as pd
import os
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio

# ==================================================
# PAGE CONFIG
# ==================================================

# set_page_config được gọi ở Home.py

# ==================================================
# PLOTLY THEME (đồng bộ với trang Sales)
# ==================================================

if "seb_dark" not in pio.templates:
    pio.templates["seb_dark"] = go.layout.Template(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e8eaed", size=12),
            xaxis=dict(gridcolor="#33373f", zerolinecolor="#33373f"),
            yaxis=dict(gridcolor="#33373f", zerolinecolor="#33373f"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            colorway=["#3b82f6", "#9ca3af", "#f59e0b", "#22d3ee", "#a78bfa", "#16a34a"],
        )
    )
pio.templates.default = "seb_dark"

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, #eceff3 0%, #dfe3e9 100%);
        border: 1px solid #e0e4ea;
        border-left: 4px solid #2563eb;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        height: 120px;
        display: flex; flex-direction: column; justify-content: flex-start;
    }
    [data-testid="stMetricDelta"] { font-size: 12px !important; margin-top: auto !important; }
    [data-testid="stMetricValue"] { font-size: 20px !important; font-weight: 700 !important; color: #111827 !important; }
    [data-testid="stMetric"] label { font-size: 11px !important; font-weight: 600 !important; color: #6b7280 !important; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# ==================================================
# CONSTANTS
# ==================================================

PNL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pnl_cache.parquet")

# Thứ tự dòng P&L (từ Sales xuống ROPA)
PNL_ORDER = [
    "Sales", "Standard Cost Of Sales", "Standard Gross Margin",
    "Generated Variances", "Variances P&L Impact", "Other Cost of Sales",
    "Gross Margin", "Direct Costs", "Storage", "Freight-out", "ASS",
    "Product Conception", "Advertising", "Operational Marketing",
    "Commercial", "G&A", "Exchange differences", "ROPA"
]

# Các dòng "subtotal" (in đậm, là kết quả cộng dồn)
SUBTOTAL_LINES = ["Sales", "Standard Gross Margin", "Gross Margin", "ROPA"]

COLORS = {"ACT": "#2563eb", "BUD": "#9ca3af", "LY": "#f59e0b",
          "POS": "#16a34a", "NEG": "#dc2626"}

# ==================================================
# HELPERS
# ==================================================

def safe_pct(num, den):
    return num / den * 100 if den else 0

# ==================================================
# LOAD DATA
# ==================================================

@st.cache_data(show_spinner="Loading P&L data...")
def load_pnl(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df.columns = df.columns.str.strip()
    # Chuyển cột filter sang category cho nhanh
    for c in ["PnL lines", "Product Line", "Key CAT", "Business Type",
              "MLA", "Distributor", "Month"]:
        if c in df.columns:
            df[c] = df[c].astype("category")
    return df

st.title("💵 P&L Dashboard")

try:
    df = load_pnl(PNL_FILE)
    if df.empty:
        st.error("Không tìm thấy file pnl_cache.parquet. Hãy chạy convert_pnl.py trước.")
        st.stop()
except Exception as e:
    st.error(f"Lỗi đọc dữ liệu P&L: {e}")
    st.stop()

# ==================================================
# SIDEBAR FILTERS
# ==================================================

st.sidebar.header("🔍 P&L Filters")

@st.cache_data(show_spinner=False)
def opts(_df, n):
    def uniq(col):
        return sorted(_df[col].dropna().astype(str).unique()) if col in _df.columns else []
    return {
        "month": sorted(_df["Month"].dropna().unique().tolist()) if "Month" in _df.columns else [],
        "biz": uniq("Business Type"),
        "pl": uniq("Product Line"),
        "cat": uniq("Key CAT"),
        "dist": uniq("Distributor"),
    }

o = opts(df, len(df))

sel_month = st.sidebar.selectbox("Month", ["All"] + [str(m) for m in o["month"]])
sel_biz   = st.sidebar.selectbox("Business Type", ["All"] + o["biz"])
sel_pl    = st.sidebar.selectbox("Product Line", ["All"] + o["pl"])
sel_cat   = st.sidebar.selectbox("Key CAT", ["All"] + o["cat"])
sel_dist  = st.sidebar.selectbox("Distributor", ["All"] + o["dist"])

# ==================================================
# FILTER
# ==================================================

mask = pd.Series(True, index=df.index)
if sel_month != "All":
    mask &= df["Month"].astype(str) == sel_month
if sel_biz != "All":
    mask &= df["Business Type"] == sel_biz
if sel_pl != "All":
    mask &= df["Product Line"] == sel_pl
if sel_cat != "All":
    mask &= df["Key CAT"] == sel_cat
if sel_dist != "All":
    mask &= df["Distributor"] == sel_dist
dff = df[mask]

# ==================================================
# BUILD P&L TABLE (cached)
# ==================================================

@st.cache_data(show_spinner=False)
def build_pnl(_d, key):
    t = _d.groupby("PnL lines", observed=True).agg(
        ACT=("Actual N", "sum"),
        BUD=("Budget N", "sum"),
        LY=("Actual N-1", "sum"),
    ).reindex(PNL_ORDER).fillna(0)
    sales = t.loc["Sales", "ACT"] if "Sales" in t.index else 0
    t["% Sales"] = t["ACT"].apply(lambda v: safe_pct(v, sales))
    t["Var BUD"] = t["ACT"] - t["BUD"]
    t["Var LY"]  = t["ACT"] - t["LY"]
    return t

cache_key = f"{sel_month}|{sel_biz}|{sel_pl}|{sel_cat}|{sel_dist}"
pnl = build_pnl(dff, cache_key)

# ==================================================
# KPI CARDS — các dòng chính
# ==================================================

def get_val(line, col):
    return pnl.loc[line, col] if line in pnl.index else 0

sales_act = get_val("Sales", "ACT")
gm_act    = get_val("Gross Margin", "ACT")
ropa_act  = get_val("ROPA", "ACT")
sgm_act   = get_val("Standard Gross Margin", "ACT")

st.subheader("Key P&L Metrics")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Sales", f"{sales_act:,.0f}",
          delta=f"{safe_pct(get_val('Sales','Var BUD'), get_val('Sales','BUD')):+.1f}% vs BUD")
k2.metric("Standard GM", f"{sgm_act:,.0f}",
          delta=f"{safe_pct(sgm_act, sales_act):.1f}% of Sales")
k3.metric("Gross Margin", f"{gm_act:,.0f}",
          delta=f"{safe_pct(gm_act, sales_act):.1f}% of Sales")
k4.metric("ROPA", f"{ropa_act:,.0f}",
          delta=f"{safe_pct(ropa_act, sales_act):.1f}% of Sales")

st.markdown("---")

# ==================================================
# TABS
# ==================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 P&L Statement", "💧 Waterfall", "📦 By Category", "🏢 By Business Type"
])

# ---- TAB 1: P&L full table ----
with tab1:
    st.subheader("P&L Statement — Actual vs Budget vs Last Year")
    disp = pnl.reset_index()
    disp.columns = ["P&L Line", "Actual N", "Budget N", "Actual N-1",
                    "% Sales", "Var vs BUD", "Var vs LY"]

    def highlight_subtotal(row):
        if row["P&L Line"] in SUBTOTAL_LINES:
            return ["font-weight: bold; background-color: rgba(59,130,246,0.12)"] * len(row)
        return [""] * len(row)

    styled = (disp.style
              .apply(highlight_subtotal, axis=1)
              .format({
                  "Actual N": "{:,.0f}", "Budget N": "{:,.0f}", "Actual N-1": "{:,.0f}",
                  "% Sales": "{:.1f}%", "Var vs BUD": "{:+,.0f}", "Var vs LY": "{:+,.0f}",
              }))
    st.dataframe(styled, use_container_width=True, hide_index=True, height=680)

# ---- TAB 2: Waterfall Sales -> GM -> ROPA ----
with tab2:
    st.subheader("P&L Waterfall (Actual N)")

    # Các bước waterfall chính
    steps = [
        ("Sales", get_val("Sales", "ACT"), "absolute"),
        ("Std COGS", get_val("Standard Cost Of Sales", "ACT"), "relative"),
        ("Std GM", None, "total"),
        ("Variances + Other", get_val("Generated Variances","ACT")
                              + get_val("Variances P&L Impact","ACT")
                              + get_val("Other Cost of Sales","ACT"), "relative"),
        ("Gross Margin", None, "total"),
        ("Direct Costs", get_val("Direct Costs","ACT"), "relative"),
        ("Logistics (Storage+Freight+ASS)",
            get_val("Storage","ACT")+get_val("Freight-out","ACT")+get_val("ASS","ACT"), "relative"),
        ("Marketing (PC+Adv+OpMkt)",
            get_val("Product Conception","ACT")+get_val("Advertising","ACT")
            +get_val("Operational Marketing","ACT"), "relative"),
        ("Commercial", get_val("Commercial","ACT"), "relative"),
        ("G&A", get_val("G&A","ACT"), "relative"),
        ("FX", get_val("Exchange differences","ACT"), "relative"),
        ("ROPA", None, "total"),
    ]

    measures = [s[2] for s in steps]
    labels   = [s[0] for s in steps]
    values   = [s[1] if s[1] is not None else 0 for s in steps]

    fig_wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        connector={"line": {"color": "#6b7280"}},
        increasing={"marker": {"color": "#16a34a"}},
        decreasing={"marker": {"color": "#dc2626"}},
        totals={"marker": {"color": "#3b82f6"}},
        text=[f"{v:,.0f}" if m != "total" else "" for v, m in zip(values, measures)],
        textposition="outside",
    ))
    fig_wf.update_layout(height=520, margin=dict(t=30, b=80), template="seb_dark",
                         xaxis_tickangle=-35)
    st.plotly_chart(fig_wf, use_container_width=True)

# ---- TAB 3: By Product Line / Key CAT ----
with tab3:
    dim = st.radio("Phân tích theo:", ["Product Line", "Key CAT"], horizontal=True)
    metric_line = st.selectbox("Chọn dòng P&L:",
                               ["Sales", "Gross Margin", "ROPA", "Standard Gross Margin"])

    sub = dff[dff["PnL lines"] == metric_line]
    by = (sub.groupby(dim, observed=True)
          .agg(ACT=("Actual N","sum"), BUD=("Budget N","sum"), LY=("Actual N-1","sum"))
          .sort_values("ACT", ascending=False).reset_index())

    fig_cat = go.Figure()
    fig_cat.add_bar(y=by[dim], x=by["ACT"], name="Actual N",
                    orientation="h", marker_color=COLORS["ACT"])
    fig_cat.add_bar(y=by[dim], x=by["BUD"], name="Budget N",
                    orientation="h", marker_color=COLORS["BUD"])
    fig_cat.add_bar(y=by[dim], x=by["LY"], name="Actual N-1",
                    orientation="h", marker_color=COLORS["LY"])
    fig_cat.update_layout(barmode="group", height=max(360, len(by)*40),
                          margin=dict(t=20,b=20), template="seb_dark",
                          title=f"{metric_line} by {dim}")
    st.plotly_chart(fig_cat, use_container_width=True)

    st.dataframe(
        by.style.format({"ACT":"{:,.0f}","BUD":"{:,.0f}","LY":"{:,.0f}"}),
        use_container_width=True, hide_index=True
    )

# ---- TAB 4: By Business Type ----
with tab4:
    st.subheader("P&L by Business Type")
    if "Business Type" in dff.columns:
        biz = (dff[dff["PnL lines"].isin(["Sales","Gross Margin","ROPA"])]
               .groupby(["Business Type","PnL lines"], observed=True)["Actual N"]
               .sum().reset_index())
        biz_pivot = biz.pivot(index="Business Type", columns="PnL lines",
                              values="Actual N").fillna(0)
        # Sắp cột theo thứ tự
        for c in ["Sales","Gross Margin","ROPA"]:
            if c not in biz_pivot.columns:
                biz_pivot[c] = 0
        biz_pivot = biz_pivot[["Sales","Gross Margin","ROPA"]]

        fig_biz = go.Figure()
        fig_biz.add_bar(x=biz_pivot.index, y=biz_pivot["Sales"], name="Sales",
                        marker_color=COLORS["ACT"])
        fig_biz.add_bar(x=biz_pivot.index, y=biz_pivot["Gross Margin"], name="Gross Margin",
                        marker_color=COLORS["LY"])
        fig_biz.add_bar(x=biz_pivot.index, y=biz_pivot["ROPA"], name="ROPA",
                        marker_color=COLORS["POS"])
        fig_biz.update_layout(barmode="group", height=440, margin=dict(t=20,b=20),
                              template="seb_dark")
        st.plotly_chart(fig_biz, use_container_width=True)

        st.dataframe(
            biz_pivot.reset_index().style.format(
                {"Sales":"{:,.0f}","Gross Margin":"{:,.0f}","ROPA":"{:,.0f}"}),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Không có cột Business Type.")
