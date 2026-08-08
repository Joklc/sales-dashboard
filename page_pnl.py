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
            font=dict(color="#0f172a", size=12),
            xaxis=dict(gridcolor="#cdd9e8", zerolinecolor="#cdd9e8"),
            yaxis=dict(gridcolor="#cdd9e8", zerolinecolor="#cdd9e8"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            colorway=["#3b82f6", "#9ca3af", "#f59e0b", "#22d3ee", "#a78bfa", "#16a34a"],
        )
    )
pio.templates.default = "seb_dark"

st.markdown("""
<style>
    /* ===== Nen trang: xanh phia tren, mo dan xuong sang ===== */
    [data-testid="stAppViewContainer"], .stApp {
        background-color: #e2e8f0;
        background-repeat: no-repeat;
    }
    .hero {
        background: transparent;
        border-radius: 18px; padding: 18px 6px 16px 6px;
        margin-bottom: 14px;
    }
    .hero-title { color: #1e293b; font-size: 28px; font-weight: 800; margin: 0; line-height: 1.1; }
    .hero-sub   { color: #64748b; font-size: 13px; margin: 6px 0 18px 0; }
    .hero-kpis  { display: flex; gap: 14px; flex-wrap: wrap; }
    .hero-tile  {
        flex: 1; min-width: 150px; background: #3b82f6;
        border: 1px solid #3b82f6; border-radius: 12px; padding: 14px 16px;
        backdrop-filter: blur(4px);
    }
    .hero-tile .lbl { color: #dbe7ff; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
    .hero-tile .val { color: #ffffff; font-size: 22px; font-weight: 800; margin-top: 4px; }
    .hero-tile .sub { color: #b9d0ff; font-size: 11px; margin-top: 2px; }
    .statcard {
        background: #3b82f6; border: 1px solid #3b82f6; border-radius: 16px;
        padding: 18px 18px 16px 18px; box-shadow: 0 6px 16px rgba(30,64,175,0.22);
        height: 118px; display: flex; flex-direction: column; justify-content: space-between;
    }
    .statcard .top { display: flex; align-items: center; justify-content: space-between; }
    .statcard .icon { width: 42px; height: 42px; border-radius: 11px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
    .statcard .val { font-size: 24px; font-weight: 800; color: #ffffff; margin-top: 6px; }
    .statcard .lbl { font-size: 11px; font-weight: 600; color: #cfe0ff; text-transform: uppercase; letter-spacing: .03em; }
    .statcard .icon { background: rgba(255,255,255,0.20) !important; }

    /* Header cac bang st.dataframe: nen xam dam, chu trang */
    [data-testid="stDataFrame"] thead tr th {
        background-color: #475569 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    [data-testid="stDataFrame"] [role="columnheader"] {
        background-color: #475569 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
    }
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

# Tieu de + KPI nam trong hero banner phia duoi

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

st.sidebar.markdown("---")
fx = st.sidebar.number_input(
    "FX → VND (1 = giữ nguyên đơn vị gốc)",
    min_value=0.0, value=1.0, step=1.0, format="%.4f",
    help="Nhập tỷ giá để quy số liệu ra VND. Vd dữ liệu đang theo triệu VND thì nhập 1000000. Để 1 nếu giữ nguyên."
)

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

# Quy doi sang VND theo FX (neu fx != 1)
if fx != 1.0:
    dff = dff.copy()
    for _c in ["Actual N", "Budget N", "Actual N-1", "Forecast 5+7"]:
        if _c in dff.columns:
            dff[_c] = dff[_c] * fx

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

cache_key = f"{sel_month}|{sel_biz}|{sel_pl}|{sel_cat}|{sel_dist}|{fx}"
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


def fmt_abbr(v):
    v = float(v)
    if abs(v) >= 1e9: return f"{v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"{v/1e6:.1f}M"
    return f"{v:,.0f}"

def stat_card(col, icon, icon_bg, icon_fg, label, value):
    col.markdown(f"""
    <div class="statcard"><div class="top">
        <div class="icon" style="background:{icon_bg};color:{icon_fg}">{icon}</div>
    </div><div>
        <div class="val">{value}</div><div class="lbl">{label}</div>
    </div></div>
    """, unsafe_allow_html=True)

_sales_var = safe_pct(get_val('Sales','Var BUD'), get_val('Sales','BUD'))
st.markdown(f"""
<div class="hero">
  <div class="hero-title">💵 ROPA</div>
  <div class="hero-sub">Actual N vs Budget vs Last Year</div>
  <div class="hero-kpis">
    <div class="hero-tile"><div class="lbl">Sales</div><div class="val">{fmt_abbr(sales_act)}</div><div class="sub">KEUR • {_sales_var:+.1f}% vs BUD</div></div>
    <div class="hero-tile"><div class="lbl">Standard GM</div><div class="val">{fmt_abbr(sgm_act)}</div><div class="sub">KEUR • {safe_pct(sgm_act, sales_act):.1f}% of Sales</div></div>
    <div class="hero-tile"><div class="lbl">Gross Margin</div><div class="val">{fmt_abbr(gm_act)}</div><div class="sub">KEUR • {safe_pct(gm_act, sales_act):.1f}% of Sales</div></div>
    <div class="hero-tile"><div class="lbl">ROPA</div><div class="val">{fmt_abbr(ropa_act)}</div><div class="sub">KEUR • {safe_pct(ropa_act, sales_act):.1f}% of Sales</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

p1, p2, p3, p4 = st.columns(4)
stat_card(p1, "💰", "#eff4ff", "#2563eb", "Std GM %", f"{safe_pct(sgm_act, sales_act):.1f}%")
stat_card(p2, "📊", "#eafaf1", "#16a34a", "Gross Margin %", f"{safe_pct(gm_act, sales_act):.1f}%")
stat_card(p3, "🎯", "#f3eefe", "#7c3aed", "ROPA %", f"{safe_pct(ropa_act, sales_act):.1f}%")
stat_card(p4, "📈", "#fef3e8", "#ea7a0c", "Sales vs BUD", f"{_sales_var:+.1f}%")
st.markdown("<br>", unsafe_allow_html=True)

# ==================================================
# TABS
# ==================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 P&L Statement", "💧 Waterfall", "📦 By Category", "🏢 By Business Type",
    "🔀 Local vs Allocated"
])

# ---- TAB 1: P&L full table ----
with tab1:
    st.subheader("P&L Statement — Actual vs Budget vs Last Year")

    col_tbl, col_chart = st.columns([3, 2], gap="medium")

    with col_tbl:
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
        st.dataframe(styled, use_container_width=True, hide_index=True, height=690)

    with col_chart:
        key_lines = ["Sales", "Standard Gross Margin", "Gross Margin", "ROPA"]
        kd = pnl.reindex(key_lines)

        # Chart 1: cac dong chinh — Actual vs Budget vs LY
        fig_key = go.Figure()
        fig_key.add_bar(y=key_lines, x=kd["LY"],  name="Actual N-1", orientation="h", marker_color=COLORS["LY"])
        fig_key.add_bar(y=key_lines, x=kd["BUD"], name="Budget N",   orientation="h", marker_color=COLORS["BUD"])
        fig_key.add_bar(y=key_lines, x=kd["ACT"], name="Actual N",   orientation="h", marker_color=COLORS["ACT"])
        fig_key.update_layout(
            barmode="group", height=330, margin=dict(t=34, b=10, l=4, r=4),
            template="seb_dark", title="Key lines — ACT vs BUD vs LY",
            yaxis=dict(autorange="reversed"),
            legend=dict(orientation="h", y=-0.18, font=dict(size=10)),
        )
        st.plotly_chart(fig_key, use_container_width=True)

        # Chart 2: % of Sales cua cac dong chinh
        fig_pct = go.Figure(go.Bar(
            x=key_lines, y=kd["% Sales"],
            marker_color=["#2563eb", "#16a34a", "#22d3ee", "#a78bfa"],
            text=[f"{v:.1f}%" for v in kd["% Sales"]], textposition="outside",
        ))
        fig_pct.update_layout(
            height=300, margin=dict(t=34, b=10, l=4, r=4), template="seb_dark",
            title="% of Sales", yaxis=dict(ticksuffix="%"), xaxis_tickangle=-15,
        )
        st.plotly_chart(fig_pct, use_container_width=True)

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

# ---- TAB 3: By Category (Product Line / Key CAT) ----
with tab3:
    dim = st.radio("Phân tích theo:", ["Product Line", "Key CAT"], horizontal=True)

    if dim in dff.columns:
        sub = dff[dff["PnL lines"].isin(["Sales", "Gross Margin", "ROPA",
                                         "Standard Gross Margin"])]
        cat = (sub.groupby([dim, "PnL lines"], observed=True)["Actual N"]
               .sum().reset_index())
        cat_pivot = cat.pivot(index=dim, columns="PnL lines",
                              values="Actual N").fillna(0)
        for c in ["Sales", "Gross Margin", "ROPA", "Standard Gross Margin"]:
            if c not in cat_pivot.columns:
                cat_pivot[c] = 0
        cat_pivot = cat_pivot[["Sales", "Gross Margin", "ROPA",
                               "Standard Gross Margin"]].reset_index()

        # % GM = GM/Sales ; % SGM = Standard GM/Sales ; % ROPA = ROPA/Sales
        def _pct(n, d):
            return (n / d * 100) if d else 0
        cat_pivot["GM%"] = cat_pivot.apply(lambda r: _pct(r["Gross Margin"], r["Sales"]), axis=1)
        cat_pivot["SGM%"] = cat_pivot.apply(lambda r: _pct(r["Standard Gross Margin"], r["Sales"]), axis=1)
        cat_pivot["% ROPA"] = cat_pivot.apply(lambda r: _pct(r["ROPA"], r["Sales"]), axis=1)
        cat_pivot = cat_pivot.sort_values("Sales", ascending=False)

        col_a, col_b = st.columns([1, 1])
        with col_a:
            # Treemap ty trong Sales (chi lay dong Sales > 0 cho dep)
            pos = cat_pivot[cat_pivot["Sales"] > 0]
            fig_tree_cat = go.Figure(go.Treemap(
                labels=pos[dim],
                parents=[""] * len(pos),
                values=pos["Sales"],
                textinfo="label+value+percent root",
                marker=dict(
                    colors=pos["Sales"],
                    colorscale=[[0, "#93c5fd"], [0.5, "#3b82f6"], [1, "#1e3a8a"]],
                    line=dict(width=2, color="#ffffff"),
                ),
                texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentRoot}",
                hovertemplate="<b>%{label}</b><br>Sales: %{value:,.0f}<br>%{percentRoot} of total<extra></extra>",
            ))
            fig_tree_cat.update_layout(height=420, margin=dict(t=36, b=10, l=0, r=0),
                                       template="seb_dark",
                                       title=f"Sales Proportion by {dim}")
            st.plotly_chart(fig_tree_cat, use_container_width=True)
        with col_b:
            st.dataframe(
                cat_pivot[[dim, "Sales", "Gross Margin", "GM%",
                           "Standard Gross Margin", "SGM%", "ROPA", "% ROPA"]]
                .rename(columns={"Standard Gross Margin": "Std GM"})
                .style.format({"Sales": "{:,.0f}", "Gross Margin": "{:,.0f}",
                               "GM%": "{:.1f}%", "Std GM": "{:,.0f}", "SGM%": "{:.1f}%",
                               "ROPA": "{:,.0f}", "% ROPA": "{:.1f}%"}),
                use_container_width=True, hide_index=True, height=420
            )
    else:
        st.info(f"Không có cột {dim}.")


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

        # Them cot % of Sales (ty trong Sales tung Business Type / tong Sales)
        tbl = biz_pivot.reset_index()
        total_sales = tbl["Sales"].sum()
        tbl["% of Sales"] = tbl["Sales"] / total_sales * 100 if total_sales else 0
        # % ROPA = ROPA / Sales cua tung Business Type (ty suat)
        tbl["% ROPA"] = tbl.apply(
            lambda r: (r["ROPA"] / r["Sales"] * 100) if r["Sales"] else 0, axis=1)
        tbl = tbl.sort_values("Sales", ascending=False)

        col_a, col_b = st.columns([1, 1])
        with col_a:
            fig_donut_biz = go.Figure(go.Pie(
                labels=tbl["Business Type"], values=tbl["Sales"], hole=0.5,
                textinfo="percent",
                marker=dict(colors=["#3b82f6", "#f59e0b", "#16a34a", "#22d3ee",
                                    "#a78bfa", "#9ca3af", "#ef4444"])
            ))
            fig_donut_biz.update_layout(height=360, margin=dict(t=30, b=10),
                                        template="seb_dark", title="Sales Proportion")
            st.plotly_chart(fig_donut_biz, use_container_width=True)
        with col_b:
            st.dataframe(
                tbl[["Business Type", "Sales", "% of Sales", "Gross Margin", "ROPA", "% ROPA"]]
                .style.format({"Sales":"{:,.0f}", "% of Sales":"{:.1f}%",
                               "Gross Margin":"{:,.0f}", "ROPA":"{:,.0f}",
                               "% ROPA":"{:.1f}%"}),
                use_container_width=True, hide_index=True, height=360
            )
    else:
        st.info("Không có cột Business Type.")


# ---- TAB 5: Local vs Allocated ----
with tab5:
    st.subheader("P&L — Local vs Allocated (Actual N-1 · Budget · Actual N)")

    if "Type" not in dff.columns:
        st.info("Không có cột Type (Local/Allocated) trong dữ liệu.")
    else:
        view_mode = st.radio(
            "Hiển thị:",
            ["VND value", "% of Sales", "% split (Local/Allocated)"],
            horizontal=True
        )

        la = (dff.groupby(["PnL lines", "Type"], observed=True)
              .agg(ACT=("Actual N", "sum"), BUD=("Budget N", "sum"), LY=("Actual N-1", "sum"))
              .reset_index())

        def _split(metric):
            w = la.pivot(index="PnL lines", columns="Type", values=metric)
            for t in ["Local", "Allocated"]:
                if t not in w.columns:
                    w[t] = 0
            return w[["Local", "Allocated"]].reindex(PNL_ORDER).fillna(0)

        act, bud, ly = _split("ACT"), _split("BUD"), _split("LY")

        # Bang gia tri goc (VND)
        val = pd.DataFrame(index=PNL_ORDER)
        val["N-1 Local"]     = ly["Local"]
        val["N-1 Allocated"] = ly["Allocated"]
        val["BUD Local"]     = bud["Local"]
        val["BUD Allocated"] = bud["Allocated"]
        val["ACT Local"]     = act["Local"]
        val["ACT Allocated"] = act["Allocated"]
        val["Total ACT"]     = val["ACT Local"] + val["ACT Allocated"]

        # Sales tong moi nhom (mau so cho % of Sales)
        def _sales_total(d):
            return (d.loc["Sales", "Local"] + d.loc["Sales", "Allocated"]) if "Sales" in d.index else 0
        sales_ly, sales_bud, sales_act = _sales_total(ly), _sales_total(bud), _sales_total(act)

        if view_mode == "VND value":
            tbl = val.copy()
            fmt = {c: "{:,.0f}" for c in tbl.columns}
            cap = "Local = chi phí phát sinh tại thị trường · Allocated = chi phí phân bổ từ tập đoàn." \
                  + ("  |  Đơn vị: VND (đã quy theo FX)." if fx != 1.0 else "")

        elif view_mode == "% of Sales":
            # Moi o chia cho Sales tong cua nhom do
            tbl = pd.DataFrame(index=PNL_ORDER)
            tbl["N-1 Local"]     = val["N-1 Local"]     / sales_ly  * 100 if sales_ly  else 0
            tbl["N-1 Allocated"] = val["N-1 Allocated"] / sales_ly  * 100 if sales_ly  else 0
            tbl["BUD Local"]     = val["BUD Local"]     / sales_bud * 100 if sales_bud else 0
            tbl["BUD Allocated"] = val["BUD Allocated"] / sales_bud * 100 if sales_bud else 0
            tbl["ACT Local"]     = val["ACT Local"]     / sales_act * 100 if sales_act else 0
            tbl["ACT Allocated"] = val["ACT Allocated"] / sales_act * 100 if sales_act else 0
            tbl["Total ACT"]     = val["Total ACT"]     / sales_act * 100 if sales_act else 0
            fmt = {c: "{:.1f}%" for c in tbl.columns}
            cap = "Mỗi ô = % so với Sales của cùng nhóm (Actual N-1 / Budget / Actual N)."

        else:  # % split Local/Allocated trong tung dong
            tbl = pd.DataFrame(index=PNL_ORDER)
            for grp, dd in [("N-1", ly), ("BUD", bud), ("ACT", act)]:
                tot = dd["Local"] + dd["Allocated"]
                tot = tot.where(tot != 0, other=pd.NA)
                tbl[f"{grp} Local %"]     = (dd["Local"]     / tot * 100)
                tbl[f"{grp} Allocated %"] = (dd["Allocated"] / tot * 100)
            tbl = tbl.fillna(0)
            fmt = {c: "{:.1f}%" for c in tbl.columns}
            cap = "Mỗi dòng: tỷ trọng Local và Allocated cộng lại = 100% (xét trong từng dòng P&L)."

        tbl = tbl.reindex(PNL_ORDER).reset_index().rename(columns={"index": "P&L Line"})

        def _hl_la(row):
            if row["P&L Line"] in SUBTOTAL_LINES:
                return ["font-weight: bold; background-color: rgba(59,130,246,0.12)"] * len(row)
            return [""] * len(row)

        st.dataframe(
            tbl.style.apply(_hl_la, axis=1).format(fmt),
            use_container_width=True, hide_index=True, height=680
        )
        st.caption(cap)
