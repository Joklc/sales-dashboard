import streamlit as st
import pandas as pd
import os
import io
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio

# ==================================================
# PAGE CONFIG
# ==================================================

# set_page_config được gọi ở Home.py

# ==================================================
# PLOTLY THEME — đồng bộ nền xám đậm
# ==================================================

pio.templates["seb_dark"] = go.layout.Template(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",   # trong suốt, ăn theo nền app
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#0f172a", size=12),
        xaxis=dict(gridcolor="#cdd9e8", zerolinecolor="#cdd9e8"),
        yaxis=dict(gridcolor="#cdd9e8", zerolinecolor="#cdd9e8"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        colorway=["#3b82f6", "#9ca3af", "#f59e0b", "#22d3ee", "#a78bfa", "#16a34a"],
    )
)
pio.templates.default = "seb_dark"

# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown("""
<style>
    /* ===== Nen trang: xanh phia tren, mo dan xuong sang ===== */
    [data-testid="stAppViewContainer"], .stApp {
        background-color: #f1f5f9;
        background-image: linear-gradient(180deg, #334155 0px, #475569 220px, rgba(241,245,249,0) 480px);
        background-repeat: no-repeat;
    }
    .hero {
        background: transparent;
        border-radius: 18px; padding: 18px 6px 16px 6px;
        margin-bottom: 14px;
    }
    .hero-title { color: #ffffff; font-size: 28px; font-weight: 800; margin: 0; line-height: 1.1; }
    .hero-sub   { color: #c7dbff; font-size: 13px; margin: 6px 0 18px 0; }
    .hero-kpis  { display: flex; gap: 14px; flex-wrap: wrap; }
    .hero-tile  {
        flex: 1; min-width: 150px; background: rgba(255,255,255,0.13);
        border: 1px solid rgba(255,255,255,0.22); border-radius: 12px; padding: 14px 16px;
        backdrop-filter: blur(4px);
    }
    .hero-tile .lbl { color: #dbe7ff; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
    .hero-tile .val { color: #ffffff; font-size: 22px; font-weight: 800; margin-top: 4px; }
    .hero-tile .sub { color: #b9d0ff; font-size: 11px; margin-top: 2px; }
    .statcard {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); border: 1px solid #1e3a8a; border-radius: 16px;
        padding: 18px 18px 16px 18px; box-shadow: 0 6px 16px rgba(30,64,175,0.22);
        height: 118px; display: flex; flex-direction: column; justify-content: space-between;
    }
    .statcard .top { display: flex; align-items: center; justify-content: space-between; }
    .statcard .icon { width: 42px; height: 42px; border-radius: 11px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
    .statcard .val { font-size: 24px; font-weight: 800; color: #ffffff; margin-top: 6px; }
    .statcard .lbl { font-size: 11px; font-weight: 600; color: #cfe0ff; text-transform: uppercase; letter-spacing: .03em; }
    .statcard .icon { background: rgba(255,255,255,0.20) !important; }
</style>
""", unsafe_allow_html=True)

# ==================================================
# CONSTANTS
# ==================================================

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

# File parquet nằm cùng folder với app.py (chạy được dù terminal đứng ở đâu, cả local lẫn cloud)
PARQUET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache.parquet")

COLORS = {
    "ACT": "#2563eb",
    "BUD": "#9ca3af",
    "LY":  "#f59e0b",
    "POS": "#16a34a",
    "NEG": "#dc2626",
}

# ==================================================
# DATA LOADING (CACHED)
# ==================================================

@st.cache_data(show_spinner="Loading data...")
def load_data(parquet_file: str) -> pd.DataFrame:
    """Đọc file parquet từ repo."""
    if not os.path.exists(parquet_file):
        return pd.DataFrame()
    df = pd.read_parquet(parquet_file)
    df.columns = df.columns.str.strip()
    return df

# ==================================================
# HELPERS
# ==================================================

def safe_pct(num, den):
    return num / den * 100 if den else 0

def variance_color(val):
    return COLORS["POS"] if val >= 0 else COLORS["NEG"]

@st.cache_data(show_spinner="Đang tạo file Excel...")
def export_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return buf.getvalue()

@st.cache_data(show_spinner="Đang tạo file Excel...")
def export_summary(df_filtered: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Product summary
        prod = (df_filtered.groupby("Product Line", as_index=False)
                .agg(NS_ACT=("NS_ACT","sum"), NS_BUD=("NS_BUD","sum"), NS_LY=("NS_LY","sum")))
        prod["VAR_%"] = prod.apply(lambda r: safe_pct(r.NS_ACT - r.NS_BUD, r.NS_BUD), axis=1)
        prod.to_excel(writer, index=False, sheet_name="Product Line")
        # MLA summary
        mla = (df_filtered.groupby("MLA name", as_index=False)
               .agg(NS_ACT=("NS_ACT","sum"), NS_BUD=("NS_BUD","sum"), NS_LY=("NS_LY","sum")))
        mla["VAR_%"] = mla.apply(lambda r: safe_pct(r.NS_ACT - r.NS_BUD, r.NS_BUD), axis=1)
        mla.to_excel(writer, index=False, sheet_name="MLA")
        # Raw
        df_filtered.to_excel(writer, index=False, sheet_name="Raw Data")
    return buf.getvalue()

# ==================================================
# LOAD DATA
# ==================================================

try:
    df = load_data(PARQUET_FILE)
    if df.empty:
        st.error("Không tìm thấy file data_cache.parquet trong repo.")
        st.stop()
except Exception as e:
    st.error(f"Lỗi đọc dữ liệu: {e}")
    st.stop()

available_months = [m for m in MONTH_ORDER if m in df["MONTH"].dropna().unique()]

# Convert filter columns to category (filter nhanh hơn trên data lớn)
for _col in ["MONTH", "Distribution Channel", "MLA name", "Product Line", "Family Level 2"]:
    if _col in df.columns:
        df[_col] = df[_col].astype("category")

# Cache dropdown options (chỉ tính 1 lần, không tính lại mỗi rerun)
@st.cache_data(show_spinner=False)
def get_filter_options(_df: pd.DataFrame, n_rows: int) -> dict:
    return {
        "channel": sorted(_df["Distribution Channel"].dropna().astype(str).unique()),
        "mla":     sorted(_df["MLA name"].dropna().astype(str).unique()),
        "product": sorted(_df["Product Line"].dropna().astype(str).unique()),
        "family":  sorted(_df["Family Level 2"].dropna().astype(str).unique()),
    }

opts = get_filter_options(df, len(df))

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.header("🔍 Filters")

selected_month = st.sidebar.selectbox(
    "Month", ["YTD"] + available_months
)

# So sánh 2 tháng
compare_mode = st.sidebar.toggle("Compare 2 Months", value=False)
compare_month = None
if compare_mode and len(available_months) >= 2:
    compare_month = st.sidebar.selectbox(
        "Compare with",
        [m for m in available_months if m != selected_month]
        if selected_month != "YTD" else available_months
    )

st.sidebar.markdown("---")

selected_channel = st.sidebar.selectbox(
    "Distribution Channel",
    ["All"] + opts["channel"]
)

selected_mla = st.sidebar.selectbox(
    "MLA Name",
    ["All"] + opts["mla"]
)

selected_product = st.sidebar.selectbox(
    "Product Line",
    ["All"] + opts["product"]
)

selected_family = st.sidebar.selectbox(
    "Family Level 2",
    ["All"] + opts["family"]
)

# ==================================================
# FILTER FUNCTION
# ==================================================

def apply_filters(data, month):
    mask = pd.Series(True, index=data.index)
    if month != "YTD":
        mask &= data["MONTH"] == month
    if selected_channel != "All":
        mask &= data["Distribution Channel"] == selected_channel
    if selected_mla != "All":
        mask &= data["MLA name"] == selected_mla
    if selected_product != "All":
        mask &= data["Product Line"] == selected_product
    if selected_family != "All":
        mask &= data["Family Level 2"] == selected_family
    return data[mask]

df_filtered = apply_filters(df, selected_month)
df_compare = apply_filters(df, compare_month) if compare_mode and compare_month else None

# ==================================================
# PRE-COMPUTE ALL AGGREGATIONS (1 lần duy nhất)
# ==================================================

@st.cache_data(show_spinner=False)
def compute_aggs(df_key: str, _df: pd.DataFrame, has_sgm: bool) -> dict:
    agg_cols = {"NS_ACT": "sum", "NS_BUD": "sum", "NS_LY": "sum"}
    if has_sgm:
        agg_cols.update({"SGM_ACT": "sum", "SGM_BUD": "sum", "SGM_LY": "sum"})

    trend = _df.groupby("MONTH", as_index=False, observed=True).agg(agg_cols)

    prod = (_df.groupby("Product Line", as_index=False, observed=True).agg(agg_cols)
            .sort_values("NS_ACT", ascending=False))

    mla = (_df.groupby("MLA name", as_index=False, observed=True).agg(agg_cols)
           .sort_values("NS_ACT", ascending=False))

    contrib = (_df.groupby("Product Line", as_index=False, observed=True)["NS_ACT"].sum()
               .sort_values("NS_ACT", ascending=False))

    fl2 = pd.DataFrame()
    if "Family Level 2" in _df.columns:
        fl2 = (_df.groupby("Family Level 2", as_index=False, observed=True).agg(agg_cols)
               .sort_values("NS_ACT", ascending=False))

    return {
        "trend": trend,
        "prod": prod,
        "mla": mla,
        "contrib": contrib,
        "fl2": fl2,
        "ns_act": _df["NS_ACT"].sum(),
        "ns_bud": _df["NS_BUD"].sum(),
        "ns_ly":  _df["NS_LY"].sum(),
        "sgm_act": _df["SGM_ACT"].sum() if has_sgm else 0,
        "sgm_bud": _df["SGM_BUD"].sum() if has_sgm else 0,
        "sgm_ly":  _df["SGM_LY"].sum() if has_sgm else 0,
    }

_cache_key = f"{selected_month}|{selected_channel}|{selected_mla}|{selected_product}|{selected_family}"
has_sgm = all(c in df.columns for c in ["SGM_ACT","SGM_BUD","SGM_LY"])
aggs = compute_aggs(_cache_key, df_filtered, has_sgm)

# ==================================================
# HEADER
# ==================================================

period_label = selected_month if selected_month != "YTD" else "Year-to-Date"
# Tieu de + KPI nam trong hero banner phia duoi (sau khi tinh KPI)

# Export buttons — chỉ tạo file Excel khi người dùng bấm (tránh chạy mỗi lần rerun)
col_ex1, col_ex2, col_ex3 = st.columns([1.2, 1, 6])
with col_ex1:
    if st.button("📥 Tạo file Export Summary"):
        st.download_button(
            "⬇️ Tải Summary.xlsx",
            data=export_summary(df_filtered),
            file_name=f"summary_{selected_month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
with col_ex2:
    if st.button("📥 Tạo file Export Raw"):
        st.download_button(
            "⬇️ Tải Raw.xlsx",
            data=export_excel(df_filtered),
            file_name=f"raw_{selected_month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown("---")

# ==================================================
# KPI — NS
# ==================================================

ns_act = aggs["ns_act"]
ns_bud = aggs["ns_bud"]
ns_ly  = aggs["ns_ly"]
achievement  = safe_pct(ns_act, ns_bud)
variance_bud = safe_pct(ns_act - ns_bud, ns_bud)
growth_ly    = safe_pct(ns_act - ns_ly,  ns_ly)

# Compare values
cmp_act = df_compare["NS_ACT"].sum() if df_compare is not None else None


def fmt_abbr(v):
    v = float(v)
    if abs(v) >= 1e9: return f"{v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"{v/1e6:.1f}M"
    return f"{v:,.0f}"

def fmt_full(v):
    """Số đầy đủ có dấu phẩy ngăn cách, dùng cho các thẻ KPI đầu trang."""
    return f"{float(v):,.0f}"

def stat_card(col, icon, icon_bg, icon_fg, label, value):
    col.markdown(f"""
    <div class="statcard"><div class="top">
        <div class="icon" style="background:{icon_bg};color:{icon_fg}">{icon}</div>
    </div><div>
        <div class="val">{value}</div><div class="lbl">{label}</div>
    </div></div>
    """, unsafe_allow_html=True)

_sgm_act = aggs["sgm_act"]
_sgm_pct = safe_pct(_sgm_act, ns_act) if has_sgm else 0
st.markdown(f"""
<div class="hero">
  <div class="hero-title">📊 Sales Dashboard — {period_label}</div>
  <div class="hero-sub">Net Sales — Actual vs Budget vs Last Year</div>
  <div class="hero-kpis">
    <div class="hero-tile"><div class="lbl">NS Actual</div><div class="val">{fmt_full(ns_act)}</div><div class="sub">{variance_bud:+.1f}% vs BUD</div></div>
    <div class="hero-tile"><div class="lbl">NS Budget</div><div class="val">{fmt_full(ns_bud)}</div><div class="sub">target</div></div>
    <div class="hero-tile"><div class="lbl">NS Last Year</div><div class="val">{fmt_full(ns_ly)}</div><div class="sub">{growth_ly:+.1f}% YoY</div></div>
    <div class="hero-tile"><div class="lbl">Achievement</div><div class="val">{achievement:.1f}%</div><div class="sub">{achievement-100:+.1f}pp vs target</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

q1, q2, q3, q4 = st.columns(4)
stat_card(q1, "📈", "#eff4ff", "#2563eb", "Variance vs BUD", f"{variance_bud:+.1f}%")
stat_card(q2, "🚀", "#eafaf1", "#16a34a", "Growth vs LY", f"{growth_ly:+.1f}%")
stat_card(q3, "💰", "#f3eefe", "#7c3aed", "SGM% Actual", f"{_sgm_pct:.1f}%" if has_sgm else "—")
stat_card(q4, "🧾", "#fef3e8", "#ea7a0c", "SGM Value", fmt_full(_sgm_act) if has_sgm else "—")
st.markdown("<br>", unsafe_allow_html=True)

# ==================================================
# TOP MOVERS vs BUDGET — theo Product Line
# ==================================================

# ==================================================
# TOP MOVERS vs BUDGET — theo Product Line (Above & Below)
# ==================================================

st.subheader("🚦 Top Movers vs Budget by Product Line (by value)")

movers_pl = aggs["prod"][["Product Line", "NS_ACT", "NS_BUD"]].copy()
movers_pl["GAP"] = movers_pl["NS_ACT"] - movers_pl["NS_BUD"]
movers_pl["VAR_%"] = movers_pl.apply(
    lambda r: safe_pct(r.NS_ACT - r.NS_BUD, r.NS_BUD), axis=1
)

def mover_label(gap, pct, bud):
    """Nhãn trên thanh: giá trị gap + %. Nếu Budget = 0 thì ghi (no BUD) thay vì +0.0%."""
    sign = "+" if gap >= 0 else ""
    pct_txt = "no BUD" if bud == 0 else f"{pct:+.1f}%"
    return f"{sign}{fmt_abbr(gap)} ({pct_txt})"

def mover_chart(d, dim, color, side):
    """Vẽ 1 chart horizontal bar cho top movers. side='up' hoặc 'down'."""
    d = d.sort_values("GAP", ascending=(side == "up"))
    labels = [mover_label(g, p, b) for g, p, b in zip(d["GAP"], d["VAR_%"], d["NS_BUD"])]
    fig = go.Figure(go.Bar(
        y=d[dim], x=d["GAP"], orientation="h",
        marker_color=color, text=labels,
        textposition="outside", cliponaxis=False,
    ))
    margin = dict(t=10, b=10, l=10, r=100) if side == "up" else dict(t=10, b=10, l=100, r=10)
    fig.update_layout(template="seb_dark", height=280, margin=margin,
                      xaxis_title="Gap vs Budget", showlegend=False)
    return fig

col_up, col_down = st.columns(2)

with col_up:
    st.markdown("#### 🟢 Top 5 Above Budget")
    top_up_pl = movers_pl[movers_pl["GAP"] > 0].sort_values("GAP", ascending=False).head(5)
    if top_up_pl.empty:
        st.info("No Product Line above budget.")
    else:
        st.plotly_chart(mover_chart(top_up_pl, "Product Line", COLORS["POS"], "up"),
                        use_container_width=True)

with col_down:
    st.markdown("#### 🔴 Top 5 Below Budget")
    top_dn_pl = movers_pl[movers_pl["GAP"] < 0].sort_values("GAP", ascending=True).head(5)
    if top_dn_pl.empty:
        st.info("No Product Line below budget.")
    else:
        st.plotly_chart(mover_chart(top_dn_pl, "Product Line", COLORS["NEG"], "down"),
                        use_container_width=True)

net_gap = movers_pl["GAP"].sum()
st.caption(f"Net gap vs Budget (all Product Lines): {fmt_abbr(net_gap)}")

# ==================================================
# TREND CHART — NS monthly + SGM% (dual axis)
# ==================================================

st.markdown("---")

st.subheader("📈 NS Monthly Trend")

trend = aggs["trend"].copy()
trend["MONTH"] = pd.Categorical(trend["MONTH"], categories=MONTH_ORDER, ordered=True)
trend = trend.sort_values("MONTH")

if has_sgm:
    trend["SGM%_ACT"] = trend.apply(lambda r: safe_pct(r["SGM_ACT"], r["NS_ACT"]), axis=1)
    trend["SGM%_BUD"] = trend.apply(lambda r: safe_pct(r["SGM_BUD"], r["NS_BUD"]), axis=1)
    trend["SGM%_LY"]  = trend.apply(lambda r: safe_pct(r["SGM_LY"],  r["NS_LY"]),  axis=1)

if compare_mode and df_compare is not None:
    trend_cmp = (df_compare.groupby("MONTH", as_index=False)
                 .agg(NS_ACT=("NS_ACT","sum")))
    trend_cmp["MONTH"] = pd.Categorical(trend_cmp["MONTH"], categories=MONTH_ORDER, ordered=True)
    trend_cmp = trend_cmp.sort_values("MONTH")

fig_trend = make_subplots(specs=[[{"secondary_y": True}]])

# Bars — trục Y trái (NS)
fig_trend.add_trace(go.Bar(
    x=trend["MONTH"], y=trend["NS_ACT"], name="NS ACT",
    marker_color=COLORS["ACT"]), secondary_y=False)
fig_trend.add_trace(go.Bar(
    x=trend["MONTH"], y=trend["NS_BUD"], name="NS BUD",
    marker_color=COLORS["BUD"]), secondary_y=False)



# Line SGM% ACT — trục Y phải
if has_sgm:
    fig_trend.add_trace(go.Scatter(
        x=trend["MONTH"], y=trend["SGM%_ACT"], name="SGM% ACT",
        mode="lines+markers+text",
        text=trend["SGM%_ACT"].round(1).astype(str) + "%",
        textposition="top center",
        line=dict(color="#22d3ee", width=2),
        marker=dict(size=7)),
        secondary_y=True)

if compare_mode and df_compare is not None:
    fig_trend.add_trace(go.Scatter(
        x=trend_cmp["MONTH"], y=trend_cmp["NS_ACT"],
        name=f"NS ACT ({compare_month})",
        mode="lines+markers", line=dict(dash="dash", color="#8b5cf6", width=2)),
        secondary_y=False)

fig_trend.update_layout(
    template="seb_dark",
    barmode="group", height=450, margin=dict(t=20, b=20),
    legend=dict(orientation="h", y=-0.15, x=0)
)
fig_trend.update_yaxes(title_text="Net Sales", secondary_y=False)
if has_sgm:
    fig_trend.update_yaxes(
        title_text="SGM%",
        secondary_y=True,
        ticksuffix="%",
        showgrid=False
    )
st.plotly_chart(fig_trend, use_container_width=True)

# ==================================================
# PRODUCT LINE CHARTS (gộp 1 figure — nhanh hơn)
# ==================================================

st.subheader("📦 Product Line Analysis")

prod_data = aggs["prod"].head(10).copy()
prod_data["VAR_%"] = prod_data.apply(
    lambda r: safe_pct(r.NS_ACT - r.NS_BUD, r.NS_BUD), axis=1
)
prod_data["Contribution %"] = safe_pct(prod_data["NS_ACT"], prod_data["NS_ACT"].sum())

fig_prod = make_subplots(
    rows=1, cols=2,
    subplot_titles=("Top 10 Product Lines — ACT vs BUD vs LY",
                    "Variance vs Budget (%)"),
    horizontal_spacing=0.12
)

# Left: grouped bar
for col_name, color, row_label in [
    ("NS_ACT", COLORS["ACT"], "ACT"),
    ("NS_BUD", COLORS["BUD"], "BUD"),
    ("NS_LY",  COLORS["LY"],  "LY"),
]:
    fig_prod.add_trace(
        go.Bar(y=prod_data["Product Line"], x=prod_data[col_name],
               name=row_label, orientation="h", marker_color=color,
               showlegend=True),
        row=1, col=1
    )

# Right: variance waterfall-style
bar_colors = [COLORS["POS"] if v >= 0 else COLORS["NEG"] for v in prod_data["VAR_%"]]
fig_prod.add_trace(
    go.Bar(y=prod_data["Product Line"], x=prod_data["VAR_%"],
           orientation="h", marker_color=bar_colors, showlegend=False,
           text=prod_data["VAR_%"].round(1).astype(str) + "%",
           textposition="outside"),
    row=1, col=2
)
fig_prod.update_layout(barmode="group", height=520, margin=dict(t=40,b=20), template="seb_dark")
st.plotly_chart(fig_prod, use_container_width=True)

# ==================================================
# SGM% ANALYSIS — by Product Line & Family Level 2
# ==================================================

if has_sgm:
    st.subheader("💰 SGM% Analysis")

    sgm_tab1, sgm_tab2 = st.tabs(["By Product Line", "By Family Level 2"])

    def build_sgm_df(base: pd.DataFrame, dim: str) -> pd.DataFrame:
        d = base.copy()
        d["SGM%_ACT"] = d.apply(lambda r: safe_pct(r["SGM_ACT"], r["NS_ACT"]), axis=1)
        d["SGM%_BUD"] = d.apply(lambda r: safe_pct(r["SGM_BUD"], r["NS_BUD"]), axis=1)
        d["SGM%_LY"]  = d.apply(lambda r: safe_pct(r["SGM_LY"],  r["NS_LY"]),  axis=1)
        d["VAR_pp"]   = d["SGM%_ACT"] - d["SGM%_BUD"]
        return d.sort_values("NS_ACT", ascending=False).head(12)

    def render_sgm(d: pd.DataFrame, dim: str):
        # Chart: SGM% ACT vs BUD vs LY (grouped horizontal bar)
        dd = d.sort_values("SGM%_ACT")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=dd[dim], x=dd["SGM%_ACT"], name="ACT",
            orientation="h", marker_color=COLORS["ACT"]))
        fig.add_trace(go.Bar(
            y=dd[dim], x=dd["SGM%_BUD"], name="BUD",
            orientation="h", marker_color=COLORS["BUD"]))
        fig.add_trace(go.Bar(
            y=dd[dim], x=dd["SGM%_LY"], name="LY",
            orientation="h", marker_color=COLORS["LY"]))
        fig.update_layout(
            template="seb_dark",
            barmode="group", height=max(360, len(dd) * 36),
            margin=dict(t=10, b=10), xaxis_ticksuffix="%",
            xaxis_title="SGM%", legend=dict(orientation="h", y=-0.12)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Table
        tbl = d[[dim, "NS_ACT", "SGM%_ACT", "SGM%_BUD", "SGM%_LY", "VAR_pp"]].copy()
        tbl.columns = [dim, "NS ACT", "SGM% ACT", "SGM% BUD", "SGM% LY", "Var (pp)"]
        st.dataframe(
            tbl.style.format({
                "NS ACT": "{:,.0f}", "SGM% ACT": "{:.1f}%",
                "SGM% BUD": "{:.1f}%", "SGM% LY": "{:.1f}%", "Var (pp)": "{:+.1f}"
            }),
            use_container_width=True, hide_index=True
        )

    with sgm_tab1:
        sgm_prod = build_sgm_df(aggs["prod"], "Product Line")
        render_sgm(sgm_prod, "Product Line")

    with sgm_tab2:
        if not aggs["fl2"].empty:
            sgm_fl2 = build_sgm_df(aggs["fl2"], "Family Level 2")
            render_sgm(sgm_fl2, "Family Level 2")
        else:
            st.info("Không có dữ liệu Family Level 2.")

# ==================================================
# MLA ANALYSIS
# ==================================================

st.subheader("👤 MLA Analysis")

mla_data = aggs["mla"].head(10).copy()
mla_data["VAR_%"] = mla_data.apply(
    lambda r: safe_pct(r.NS_ACT - r.NS_BUD, r.NS_BUD), axis=1
)

fig_mla = make_subplots(
    rows=1, cols=2,
    subplot_titles=("Top 10 MLA — ACT vs BUD vs LY", "Variance vs Budget (%)"),
    horizontal_spacing=0.12
)

for col_name, color, row_label in [
    ("NS_ACT", COLORS["ACT"], "ACT"),
    ("NS_BUD", COLORS["BUD"], "BUD"),
    ("NS_LY",  COLORS["LY"],  "LY"),
]:
    fig_mla.add_trace(
        go.Bar(y=mla_data["MLA name"], x=mla_data[col_name],
               name=row_label, orientation="h", marker_color=color,
               showlegend=True),
        row=1, col=1
    )

mla_colors = [COLORS["POS"] if v >= 0 else COLORS["NEG"] for v in mla_data["VAR_%"]]
fig_mla.add_trace(
    go.Bar(y=mla_data["MLA name"], x=mla_data["VAR_%"],
           orientation="h", marker_color=mla_colors, showlegend=False,
           text=mla_data["VAR_%"].round(1).astype(str) + "%",
           textposition="outside"),
    row=1, col=2
)
fig_mla.update_layout(barmode="group", height=520, margin=dict(t=40,b=20), template="seb_dark")
st.plotly_chart(fig_mla, use_container_width=True)

# ==================================================
# DRILL-DOWN — MLA hoặc Channel
# ==================================================

st.subheader("🔎 Drill-Down")

drill_tab1, drill_tab2 = st.tabs(["By MLA", "By Distribution Channel"])

with drill_tab1:
    drill_mla = st.selectbox(
        "Select MLA to drill down",
        ["All (Tổng)"] + sorted(df_filtered["MLA name"].dropna().unique().tolist()),
        key="drill_mla"
    )
    if drill_mla == "All (Tổng)":
        df_drill_mla = df_filtered
    else:
        df_drill_mla = df_filtered[df_filtered["MLA name"] == drill_mla]
    drill_prod = (df_drill_mla.groupby("Product Line", as_index=False, observed=True)
                  .agg(NS_ACT=("NS_ACT","sum"), NS_BUD=("NS_BUD","sum"), NS_LY=("NS_LY","sum"))
                  .sort_values("NS_ACT", ascending=False))
    drill_prod["VAR_%"] = drill_prod.apply(
        lambda r: safe_pct(r.NS_ACT - r.NS_BUD, r.NS_BUD), axis=1
    )
    st.dataframe(
        drill_prod.style.format({"NS_ACT":"{:,.0f}","NS_BUD":"{:,.0f}",
                                 "NS_LY":"{:,.0f}","VAR_%":"{:.1f}%"}),
        use_container_width=True, hide_index=True
    )

with drill_tab2:
    drill_ch = st.selectbox(
        "Select Channel to drill down",
        ["All (Tổng)"] + sorted(df_filtered["Distribution Channel"].dropna().unique().tolist()),
        key="drill_ch"
    )
    if drill_ch == "All (Tổng)":
        df_drill_ch = df_filtered
    else:
        df_drill_ch = df_filtered[df_filtered["Distribution Channel"] == drill_ch]
    drill_prod_ch = (df_drill_ch.groupby("Product Line", as_index=False, observed=True)
                     .agg(NS_ACT=("NS_ACT","sum"), NS_BUD=("NS_BUD","sum"), NS_LY=("NS_LY","sum"))
                     .sort_values("NS_ACT", ascending=False))
    drill_prod_ch["VAR_%"] = drill_prod_ch.apply(
        lambda r: safe_pct(r.NS_ACT - r.NS_BUD, r.NS_BUD), axis=1
    )
    st.dataframe(
        drill_prod_ch.style.format({"NS_ACT":"{:,.0f}","NS_BUD":"{:,.0f}",
                                    "NS_LY":"{:,.0f}","VAR_%":"{:.1f}%"}),
        use_container_width=True, hide_index=True
    )

# ==================================================
# WINNERS / LOSERS / CONTRIBUTION (gộp tabs)
# ==================================================

st.subheader("🏆 Winners & Losers")

wl_tab1, wl_tab2, wl_tab3 = st.tabs(["Top Winners", "Top Losers", "Contribution Mix"])

all_var = aggs["prod"][["Product Line","NS_ACT","NS_BUD"]].copy()
all_var["VAR_%"] = all_var.apply(
    lambda r: safe_pct(r.NS_ACT - r.NS_BUD, r.NS_BUD), axis=1
)

fmt = {"NS_ACT":"{:,.0f}","NS_BUD":"{:,.0f}","VAR_%":"{:.1f}%"}

with wl_tab1:
    st.dataframe(all_var.sort_values("VAR_%", ascending=False).head(10)
                 .style.format(fmt), use_container_width=True)

with wl_tab2:
    st.dataframe(all_var.sort_values("VAR_%", ascending=True).head(10)
                 .style.format(fmt), use_container_width=True)

with wl_tab3:
    contrib = aggs["contrib"].copy()
    contrib["Contribution %"] = safe_pct(contrib["NS_ACT"], contrib["NS_ACT"].sum())

    c_left, c_right = st.columns([1,1])
    with c_left:
        st.dataframe(
            contrib.style.format({"NS_ACT":"{:,.0f}","Contribution %":"{:.1f}%"}),
            use_container_width=True
        )
    with c_right:
        fig_pie = go.Figure(go.Pie(
            labels=contrib["Product Line"],
            values=contrib["NS_ACT"],
            hole=0.5,
            textinfo="label+percent"
        ))
        fig_pie.update_layout(height=420, margin=dict(t=10,b=10), template="seb_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

# ==================================================
# SGM% GAP BRIDGE (Actual − Budget) — Mix effect vs SGM% effect
# ==================================================

if has_sgm and not aggs["fl2"].empty:
    st.markdown("---")
    st.subheader("🔬 SGM% Gap Bridge (Actual − Budget) — by Family Level 2")
    st.caption(
        "Tách chênh lệch SGM% tổng thành 2 nguyên nhân:  "
        "**Mix effect** = do tỷ trọng doanh số dịch chuyển giữa các Family  •  "
        "**SGM% effect** = do bản thân biên của từng Family thay đổi.  "
        "Đơn vị: điểm phần trăm (pp)."
    )

    br = aggs["fl2"][["Family Level 2", "NS_ACT", "NS_BUD", "SGM_ACT", "SGM_BUD"]].copy()

    tot_ns_act = br["NS_ACT"].sum()
    tot_ns_bud = br["NS_BUD"].sum()

    # SGM% từng dòng
    br["SGM%_ACT"] = br.apply(lambda r: safe_pct(r["SGM_ACT"], r["NS_ACT"]), axis=1)
    br["SGM%_BUD"] = br.apply(lambda r: safe_pct(r["SGM_BUD"], r["NS_BUD"]), axis=1)

    # Tỷ trọng doanh số (contribution mix), tính theo phần trăm
    br["MIX_ACT"] = br["NS_ACT"] / tot_ns_act * 100 if tot_ns_act else 0
    br["MIX_BUD"] = br["NS_BUD"] / tot_ns_bud * 100 if tot_ns_bud else 0

    # SGM% tổng của kỳ Budget — dùng làm mốc cho mix effect
    sgm_pct_bud_total = safe_pct(br["SGM_BUD"].sum(), tot_ns_bud)

    # Mix effect  = (tỷ trọng ACT − tỷ trọng BUD) × (SGM%_BUD của dòng − SGM%_BUD tổng) / 100
    # SGM% effect = (SGM%_ACT − SGM%_BUD) × tỷ trọng ACT / 100
    br["MIX_EFFECT"] = (br["MIX_ACT"] - br["MIX_BUD"]) * (br["SGM%_BUD"] - sgm_pct_bud_total) / 100
    br["SGM_EFFECT"] = (br["SGM%_ACT"] - br["SGM%_BUD"]) * br["MIX_ACT"] / 100
    br["TOTAL_IMPACT"] = br["MIX_EFFECT"] + br["SGM_EFFECT"]

    br = br.sort_values("TOTAL_IMPACT")

    # ----- Tóm tắt -----
    sgm_pct_act_total = safe_pct(br["SGM_ACT"].sum(), tot_ns_act)
    gap_total = sgm_pct_act_total - sgm_pct_bud_total
    mix_total = br["MIX_EFFECT"].sum()
    rate_total = br["SGM_EFFECT"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("SGM% Actual", f"{sgm_pct_act_total:.2f}%")
    k2.metric("SGM% Budget", f"{sgm_pct_bud_total:.2f}%")
    k3.metric("Gap", f"{gap_total:+.2f} pp")
    k4.metric("Mix / SGM% effect", f"{mix_total:+.2f} / {rate_total:+.2f} pp")

    bridge_tab1, bridge_tab2 = st.tabs(["📊 Waterfall", "📋 Bảng chi tiết"])

    # ---- Waterfall ----
    with bridge_tab1:
        top_n_br = st.slider("Số Family hiển thị (theo mức tác động lớn nhất):",
                             5, 30, 12, key="bridge_top")
        br_rank = br.reindex(br["TOTAL_IMPACT"].abs().sort_values(ascending=False).index)
        top_items = br_rank.head(top_n_br).sort_values("TOTAL_IMPACT")
        others_impact = br_rank.iloc[top_n_br:]["TOTAL_IMPACT"].sum()

        labels = ["SGM% Budget"] + top_items["Family Level 2"].tolist()
        values = [sgm_pct_bud_total] + top_items["TOTAL_IMPACT"].tolist()
        measures = ["absolute"] + ["relative"] * len(top_items)

        if abs(others_impact) > 1e-9:
            labels.append("Others")
            values.append(others_impact)
            measures.append("relative")

        labels.append("SGM% Actual")
        values.append(sgm_pct_act_total)
        measures.append("total")

        fig_br = go.Figure(go.Waterfall(
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            text=[f"{v:+.2f}" if m == "relative" else f"{v:.2f}%"
                  for v, m in zip(values, measures)],
            textposition="outside",
            connector=dict(line=dict(color="#9ca3af")),
            increasing=dict(marker=dict(color=COLORS["POS"])),
            decreasing=dict(marker=dict(color=COLORS["NEG"])),
            totals=dict(marker=dict(color=COLORS["ACT"])),
        ))
        fig_br.update_layout(template="seb_dark", height=520,
                             margin=dict(t=30, b=140),
                             yaxis_title="SGM% (pp)",
                             xaxis_tickangle=-40, showlegend=False)
        st.plotly_chart(fig_br, use_container_width=True)

    # ---- Bảng chi tiết ----
    with bridge_tab2:
        show_br = br[["Family Level 2", "NS_ACT", "SGM%_ACT", "MIX_ACT",
                      "NS_BUD", "SGM%_BUD", "MIX_BUD",
                      "MIX_EFFECT", "SGM_EFFECT", "TOTAL_IMPACT"]].copy()
        show_br.columns = ["Family Level 2", "NS Actual", "SGM% Act", "Mix% Act",
                           "NS Budget", "SGM% Bud", "Mix% Bud",
                           "Mix effect", "SGM% effect", "Total impact"]

        def color_impact(v):
            """To mau do/xanh theo gia tri, khong can matplotlib."""
            try:
                v = float(v)
            except (TypeError, ValueError):
                return ""
            if v > 0.001:
                return "color: #16a34a; font-weight: 700;"
            if v < -0.001:
                return "color: #dc2626; font-weight: 700;"
            return ""

        st.dataframe(
            show_br.style.format({
                "NS Actual": "{:,.0f}", "NS Budget": "{:,.0f}",
                "SGM% Act": "{:.2f}%", "SGM% Bud": "{:.2f}%",
                "Mix% Act": "{:.2f}%", "Mix% Bud": "{:.2f}%",
                "Mix effect": "{:+.3f}", "SGM% effect": "{:+.3f}",
                "Total impact": "{:+.3f}",
            }).map(color_impact, subset=["Mix effect", "SGM% effect", "Total impact"]),
            use_container_width=True, hide_index=True, height=520
        )
        st.caption("Mix effect / SGM% effect / Total impact tính bằng điểm phần trăm (pp). "
                   "Tổng cột Total impact = chênh lệch SGM% Actual vs Budget.")

# ==================================================
# DETAIL TABLE
# ==================================================

with st.expander(f"📋 Detail Data ({len(df_filtered):,} rows — hiển thị tối đa 1000 dòng đầu)", expanded=False):
    st.dataframe(df_filtered.head(1000), use_container_width=True)
    if len(df_filtered) > 1000:
        st.caption("💡 Chỉ hiện 1000 dòng đầu để tải nhanh. Dùng nút Export Raw để lấy toàn bộ data.")
