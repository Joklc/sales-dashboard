import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.io as pio

# ==================================================
# PLOTLY THEME (đồng bộ)
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

# ==================================================
# CONSTANTS
# ==================================================

KAM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kam_cache.parquet")
COLORS = {"ACT": "#2563eb", "BUD": "#9ca3af", "LY": "#f59e0b"}

def safe_pct(num, den):
    return num / den * 100 if den else 0

# ==================================================
# LOAD DATA
# ==================================================

@st.cache_data(show_spinner="Loading KAM MTD data...")
def load_kam(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)

try:
    df = load_kam(KAM_FILE)
    if df.empty:
        st.error("File kam_cache.parquet not found. Please run convert_kam.py first.")
        st.stop()
except Exception as e:
    st.error(f"Error reading KAM data: {e}")
    st.stop()

as_of = df["As_of"].iloc[0] if "As_of" in df.columns and len(df) else None
as_of_str = pd.to_datetime(as_of).strftime("%d-%b-%Y %H:%M") if as_of is not None else "N/A"

st.title("⚡ KAM_MTD realtime")
st.caption(f"Data updated at: {as_of_str}")

# ==================================================
# SIDEBAR: chọn góc nhìn KAM/FIN + filter
# ==================================================

st.sidebar.header("🔍 KAM MTD Filters")

view = st.sidebar.radio("Costing view", ["KAM", "FIN"], horizontal=True,
                        help="KAM = Key Account view, FIN = Finance view. They differ in COGS → SGM.")
NET = f"Net_{view}"
SGM = f"SGM_{view}"

# Tạo cột chuẩn theo góc nhìn đang chọn
df = df.copy()
df["Net"] = df[NET]
df["SGM"] = df[SGM]

# Loại các dòng Net = 0 theo góc nhìn đang chọn (giống cách filter trong Excel:
# dòng có giá vốn nhưng Net = 0 sẽ làm sai SGM%, nên bỏ ra)
df = df[df["Net"] != 0]

st.sidebar.markdown("---")

def opts(col):
    vals = sorted(df[col].dropna().astype(str).unique())
    return [v for v in vals if v.strip() != ""]

sel_ch  = st.sidebar.selectbox("Channel", ["All"] + opts("Channel"))
sel_pl  = st.sidebar.selectbox("Product Line", ["All"] + opts("Product Line"))
sel_mla = st.sidebar.selectbox("MLA", ["All"] + opts("MLA"))
search  = st.sidebar.text_input("Search Item / Comm code / item name", "")

mask = pd.Series(True, index=df.index)
if sel_ch  != "All": mask &= df["Channel"] == sel_ch
if sel_pl  != "All": mask &= df["Product Line"] == sel_pl
if sel_mla != "All": mask &= df["MLA"] == sel_mla
if search.strip():
    s = search.strip().lower()
    mask &= (
        df["Item code"].astype(str).str.lower().str.contains(s, na=False) |
        df["Comm code"].astype(str).str.lower().str.contains(s, na=False) |
        df["Item name"].astype(str).str.lower().str.contains(s, na=False)
    )
dff = df[mask]

if dff.empty:
    st.warning("No rows match the filters. Please loosen the filters.")
    st.stop()

# ==================================================
# KPI CARDS
# ==================================================

tot_gross = dff["Gross"].sum()
tot_net   = dff["Net"].sum()
tot_sgm   = dff["SGM"].sum()
tot_ded   = tot_gross - tot_net
sgm_pct   = safe_pct(tot_sgm, tot_net)
ded_pct   = safe_pct(tot_ded, tot_gross)

st.subheader(f"MTD Summary — {view} view")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Gross Sales (MTD)", f"{tot_gross:,.0f}")
c2.metric("Net Sales (MTD)", f"{tot_net:,.0f}")
c3.metric("Sale Deduction", f"{tot_ded:,.0f}")
c4.metric("Deduction %", f"{ded_pct:.1f}%")
c5.metric(f"SGM ({view})", f"{tot_sgm:,.0f}")
c6.metric(f"SGM % ({view})", f"{sgm_pct:.1f}%")

c7, c8, c9, c10 = st.columns(4)
c7.metric("No. of MLA", f"{dff['MLA'].nunique()}")
c8.metric("No. of Items", f"{dff['Item code'].nunique()}")
c9.metric("No. of Customers", f"{dff['Customer'].nunique()}")
c10.metric("Total Qty", f"{dff['Qty'].sum():,.0f}")

st.markdown("---")

def agg_by(data, dim):
    t = (data.groupby(dim, as_index=False, observed=True)
         .agg(Gross=("Gross", "sum"), Net=("Net", "sum"), SGM=("SGM", "sum")))
    t = t[t[dim].astype(str).str.strip() != ""]
    t["Deduction"] = t["Gross"] - t["Net"]
    t["Deduct%"] = t.apply(lambda r: safe_pct(r["Deduction"], r["Gross"]), axis=1)
    t["SGM%"] = t.apply(lambda r: safe_pct(r["SGM"], r["Net"]), axis=1)
    return t.sort_values("Net", ascending=False)

fmt = {"Gross": "{:,.0f}", "Net": "{:,.0f}", "Deduction": "{:,.0f}",
       "Deduct%": "{:.1f}%", "SGM": "{:,.0f}", "SGM%": "{:.1f}%"}

# ==================================================
# TABS
# ==================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 By Channel", "👤 By MLA", "📦 By Product Line", "📋 Detail Table"
])

# ---- By Channel ----
with tab1:
    by_ch = agg_by(dff, "Channel")
    fig = go.Figure()
    fig.add_bar(x=by_ch["Channel"], y=by_ch["Gross"], name="Gross", marker_color=COLORS["BUD"])
    fig.add_bar(x=by_ch["Channel"], y=by_ch["Net"], name="Net", marker_color=COLORS["ACT"])
    fig.add_scatter(x=by_ch["Channel"], y=by_ch["SGM%"], name="SGM%",
                    mode="lines+markers+text",
                    text=by_ch["SGM%"].round(1).astype(str) + "%",
                    textposition="top center",
                    line=dict(color="#22d3ee", width=2), yaxis="y2")
    fig.update_layout(barmode="group", height=440, margin=dict(t=20, b=20),
                      template="seb_dark", yaxis=dict(title="Sales"),
                      yaxis2=dict(title="SGM%", overlaying="y", side="right",
                                  ticksuffix="%", showgrid=False),
                      legend=dict(orientation="h", y=-0.2), xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(by_ch[["Channel", "Gross", "Net", "Deduction", "Deduct%", "SGM", "SGM%"]]
                 .style.format(fmt), use_container_width=True, hide_index=True)

# ---- By MLA ----
with tab2:
    top_n = st.slider("Show top MLA by Net Sales:", 5, 35, 15, key="kam_mla_top")
    by_mla = agg_by(dff, "MLA").head(top_n)
    fig_mla = go.Figure()
    fig_mla.add_bar(y=by_mla["MLA"], x=by_mla["Net"], orientation="h",
                    marker_color=COLORS["ACT"],
                    text=by_mla["Net"].apply(lambda v: f"{v:,.0f}"),
                    textposition="outside")
    fig_mla.update_layout(height=max(400, top_n * 32), margin=dict(t=20, b=20),
                          template="seb_dark", title="Net Sales by MLA",
                          yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_mla, use_container_width=True)
    st.dataframe(by_mla[["MLA", "Gross", "Net", "Deduction", "Deduct%", "SGM", "SGM%"]]
                 .style.format(fmt), use_container_width=True, hide_index=True)

# ---- By Product Line ----
with tab3:
    pl = agg_by(dff, "Product Line")
    fig_pl = go.Figure()
    fig_pl.add_bar(x=pl["Product Line"], y=pl["Net"], name="Net Sales",
                   marker_color=COLORS["ACT"],
                   text=pl["Net"].apply(lambda v: f"{v/1e9:.1f}B"),
                   textposition="outside")
    fig_pl.add_scatter(x=pl["Product Line"], y=pl["SGM%"], name="SGM%",
                       mode="lines+markers+text",
                       text=pl["SGM%"].round(1).astype(str) + "%",
                       textposition="top center",
                       line=dict(color="#22d3ee", width=2), yaxis="y2")
    fig_pl.update_layout(height=460, margin=dict(t=30, b=80), template="seb_dark",
                         yaxis=dict(title="Net Sales"),
                         yaxis2=dict(title="SGM%", overlaying="y", side="right",
                                     ticksuffix="%", showgrid=False),
                         legend=dict(orientation="h", y=-0.25), xaxis_tickangle=-30,
                         title=f"Net Sales & SGM% by Product Line ({view})")
    st.plotly_chart(fig_pl, use_container_width=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        fig_donut = go.Figure(go.Pie(
            labels=pl["Product Line"], values=pl["Net"], hole=0.5, textinfo="percent",
            marker=dict(colors=["#3b82f6", "#22d3ee", "#a78bfa", "#f59e0b",
                                "#16a34a", "#9ca3af", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316"])
        ))
        fig_donut.update_layout(height=380, margin=dict(t=30, b=10),
                                template="seb_dark", title="Net Sales Proportion")
        st.plotly_chart(fig_donut, use_container_width=True)
    with col_b:
        st.dataframe(pl[["Product Line", "Gross", "Net", "Deduction", "SGM", "SGM%"]]
                     .style.format(fmt), use_container_width=True, hide_index=True, height=380)

# ---- Detail Table ----
with tab4:
    st.subheader(f"Detail ({len(dff):,} rows) — {view} view")
    show = dff[["Channel", "MLA", "Customer", "Product Line", "Item code",
                "Comm code", "Item name", "Qty", "Gross", "Net", "SGM"]].copy()
    st.dataframe(
        show.style.format({"Qty": "{:,.0f}", "Gross": "{:,.0f}",
                           "Net": "{:,.0f}", "SGM": "{:,.0f}"}),
        use_container_width=True, hide_index=True, height=600
    )
