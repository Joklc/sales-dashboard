import streamlit as st
import pandas as pd
import os
import sys
import subprocess
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
        background: #3b82f6;
        border: 1px solid #3b82f6; border-radius: 16px;
        padding: 16px 18px 16px 18px; box-shadow: 0 6px 16px rgba(30,64,175,0.22);
        height: 140px; display: flex; flex-direction: column;
    }
    .statcard .icon {
        width: 40px; height: 40px; border-radius: 11px;
        display: flex; align-items: center; justify-content: center; font-size: 19px;
        background: rgba(255,255,255,0.20); margin-bottom: auto;
    }
    .statcard .val { font-size: 24px; font-weight: 800; color: #ffffff; line-height: 1.1; }
    .statcard .lbl { font-size: 11px; font-weight: 600; color: #cfe0ff; text-transform: uppercase; letter-spacing: .03em; margin-top: 6px; }

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

KAM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kam_cache.parquet")
COLORS = {"ACT": "#2563eb", "BUD": "#9ca3af", "LY": "#f59e0b",
          "POS": "#16a34a", "NEG": "#dc2626"}

def safe_pct(num, den):
    return num / den * 100 if den else 0

# ==================================================
# LOAD DATA
# ==================================================

@st.cache_data(show_spinner="Loading Sales MTD data...")
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
    st.error(f"Error reading Sales MTD data: {e}")
    st.stop()

as_of = df["As_of"].iloc[0] if "As_of" in df.columns and len(df) else None
as_of_str = pd.to_datetime(as_of).strftime("%d-%b-%Y %H:%M") if as_of is not None else "N/A"

# Tieu de + KPI nam trong hero banner phia duoi

# ==================================================
# SIDEBAR: chọn góc nhìn KAM/FIN + filter
# ==================================================

st.sidebar.header("🔍 Sales MTD Filters")

# ----- Nut Refresh: CHI hien khi chay LOCAL (co convert_kam.py va vao duoc o mang) -----
# Tren cloud: convert_kam.py van co nhung o mang X khong ton tai -> an nut de dong nghiep khong bam nham.
CONVERT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "convert_kam.py")

# O mang chi ton tai o may local trong cong ty
LOCAL_NETWORK_DRIVE = r"X:\Finance 2.Controlling"
is_local = os.path.exists(CONVERT_SCRIPT) and os.path.isdir(LOCAL_NETWORK_DRIVE)

if is_local:
    if st.sidebar.button("🔄 Refresh data (chay lai mapping)", use_container_width=True):
        with st.spinner("Dang doc file moi va tinh lai... (co the mat 1-2 phut)"):
            try:
                result = subprocess.run(
                    [sys.executable, CONVERT_SCRIPT],
                    capture_output=True, text=True, timeout=600,
                    cwd=os.path.dirname(CONVERT_SCRIPT),
                )
                if result.returncode == 0:
                    load_kam.clear()          # xoa cache de doc parquet moi
                    st.sidebar.success("Da cap nhat xong! Nho git push de cloud cap nhat.")
                    st.rerun()
                else:
                    st.sidebar.error("Co loi khi chay convert_kam.py")
                    st.sidebar.code((result.stderr or result.stdout)[-1500:])
            except subprocess.TimeoutExpired:
                st.sidebar.error("Qua thoi gian cho (600s). Kiem tra ket noi o mang X.")
            except Exception as e:
                st.sidebar.error(f"Loi: {e}")
    st.sidebar.markdown("---")


view = st.sidebar.radio("View as", ["KAM", "FIN"], horizontal=True,
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


def fmt_abbr(v):
    v = float(v)
    if abs(v) >= 1e9: return f"{v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"{v/1e6:.1f}M"
    return f"{v:,.0f}"

def fmt_full(v):
    """Số đầy đủ có dấu phẩy ngăn cách, dùng cho các thẻ KPI."""
    return f"{float(v):,.0f}"

def stat_card(col, icon, icon_bg, icon_fg, label, value):
    col.markdown(f"""
    <div class="statcard">
      <div class="icon">{icon}</div>
      <div class="val">{value}</div>
      <div class="lbl">{label}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div class="hero">
  <div class="hero-title">⚡ Sales_MTD realtime</div>
  <div class="hero-sub">Data updated at: {as_of_str}  •  Costing view: {view}</div>
  <div class="hero-kpis">
    <div class="hero-tile"><div class="lbl">Gross Sales</div><div class="val">{fmt_full(tot_gross)}</div><div class="sub">VND</div></div>
    <div class="hero-tile"><div class="lbl">Net Sales</div><div class="val">{fmt_full(tot_net)}</div><div class="sub">VND</div></div>
    <div class="hero-tile"><div class="lbl">SGM ({view})</div><div class="val">{fmt_full(tot_sgm)}</div><div class="sub">VND</div></div>
    <div class="hero-tile"><div class="lbl">SGM % ({view})</div><div class="val">{sgm_pct:.1f}%</div><div class="sub">of Net Sales</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

s1, s2, s3, s4 = st.columns(4)
stat_card(s1, "💸", "#eff4ff", "#2563eb", "Sale Deduction", fmt_full(tot_ded))
stat_card(s2, "📉", "#fef3e8", "#ea7a0c", "Deduction %", f"{ded_pct:.1f}%")
stat_card(s3, "🏢", "#eafaf1", "#16a34a", "No. of MLA", f"{dff['MLA'].nunique()}")
stat_card(s4, "📦", "#f3eefe", "#7c3aed", "Total Volume",
          f"{dff['Qty'].sum():,.0f}" if "Qty" in dff.columns else "—")
st.markdown("<br>", unsafe_allow_html=True)

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

tab1, tab2, tab3, tab5, tab4 = st.tabs([
    "📊 By Channel", "👤 By MLA", "📦 By Product Line",
    "🧩 Contribution Mix", "📋 Detail Table"
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

# ---- Contribution Mix ----
with tab5:
    st.subheader(f"Contribution Mix — {view} view")
    st.caption("Moi MLA dong gop bao nhieu Net vao tung Product Line, ty trong %, va SGM%.")

    # ===== Bang MLA x Product Line (Actual) =====
    piv_net = dff.pivot_table(index="MLA", columns="Product Line",
                              values="Net", aggfunc="sum", observed=True).fillna(0)
    piv_net["TOTAL"] = piv_net.sum(axis=1)
    piv_net = piv_net.sort_values("TOTAL", ascending=False)

    grand_total = piv_net["TOTAL"].sum()
    piv_show = piv_net.copy()
    piv_show["Mix %"] = piv_show["TOTAL"] / grand_total * 100 if grand_total else 0

    st.markdown("#### Net Sales by MLA × Product Line")
    num_cols = [c for c in piv_show.columns if c != "Mix %"]
    fmt_piv = {c: "{:,.0f}" for c in num_cols}
    fmt_piv["Mix %"] = "{:.1f}%"
    st.dataframe(
        piv_show.style.format(fmt_piv),
        use_container_width=True, height=460
    )

    # ===== So sanh Product Line: Actual vs F5+7 =====
    st.markdown("---")
    st.markdown("#### Actual vs Forecast — by Product Line")

    FC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forecast_cache.parquet")

    if not os.path.exists(FC_FILE):
        st.info("Chua co forecast_cache.parquet. Chay convert_forecast.py de so voi F5+7.")
    else:
        df_fc = pd.read_parquet(FC_FILE)
        MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        # Bang anh xa ten Product Line: Forecast (AND) -> Actual (&)
        PL_MAP = {
            "COOKWARE AND BAKEWARE":      "COOKWARE & BAKEWARE",
            "KITCHENWARE AND DINNERWARE": "KITCHENWARE & DINNER",
            "SPARE PARTS AND OTHERS":     "SPARE PARTS & OTHERS",
        }

        def norm_pl(s):
            s = " ".join(str(s).strip().upper().split())
            return PL_MAP.get(s, s)

        fc_rounds = sorted(df_fc["Forecast"].dropna().unique())
        fc_months = [m for m in MONTH_ORDER if m in df_fc["MONTH"].unique()]

        c1, c2 = st.columns(2)
        sel_round = c1.selectbox("Forecast round", fc_rounds,
                                 index=fc_rounds.index("F5+7") if "F5+7" in fc_rounds else 0)
        # Mac dinh thang moi nhat co forecast
        sel_m = c2.selectbox("Month (so Actual MTD voi thang nay cua forecast)",
                             fc_months, index=len(fc_months) - 1 if fc_months else 0)

        fc = df_fc[(df_fc["Forecast"] == sel_round) & (df_fc["MONTH"] == sel_m)].copy()
        # F5+7 theo KVND (nghin VND), KAM theo VND day du -> nhan forecast x 1000
        FC_UNIT = 1000
        fc_pl = (fc.groupby("Product Line", as_index=False, observed=True)
                 .agg(NS_FC=("NS_FC", "sum"), SGM_FC=("SGM_FC", "sum")))
        fc_pl["NS_FC"] = fc_pl["NS_FC"] * FC_UNIT
        fc_pl["SGM_FC"] = fc_pl["SGM_FC"] * FC_UNIT
        fc_pl["KEY"] = fc_pl["Product Line"].map(norm_pl)
        # Gop lai neu nhieu ten forecast tro ve cung 1 ten chuan
        fc_pl = fc_pl.groupby("KEY", as_index=False).agg(
            NS_FC=("NS_FC", "sum"), SGM_FC=("SGM_FC", "sum"))

        # Actual theo Product Line (tu KAM dang loc)
        act_pl = (dff.groupby("Product Line", as_index=False, observed=True)
                  .agg(NS_ACT=("Net", "sum"), SGM_ACT=("SGM", "sum")))
        act_pl["KEY"] = act_pl["Product Line"].map(norm_pl)
        act_pl = act_pl.groupby("KEY", as_index=False).agg(
            NS_ACT=("NS_ACT", "sum"), SGM_ACT=("SGM_ACT", "sum"))

        cmp = act_pl.merge(fc_pl, on="KEY", how="outer")
        cmp["Product Line"] = cmp["KEY"].str.title()
        for c in ["NS_ACT", "SGM_ACT", "NS_FC", "SGM_FC"]:
            cmp[c] = pd.to_numeric(cmp[c], errors="coerce").fillna(0)
        cmp = cmp[(cmp["NS_ACT"] != 0) | (cmp["NS_FC"] != 0)]

        cmp["GAP"] = cmp["NS_ACT"] - cmp["NS_FC"]
        cmp["VAR_%"] = cmp.apply(lambda r: safe_pct(r["NS_ACT"] - r["NS_FC"], r["NS_FC"]), axis=1)
        cmp["SGM%_ACT"] = cmp.apply(lambda r: safe_pct(r["SGM_ACT"], r["NS_ACT"]), axis=1)
        cmp["SGM%_FC"] = cmp.apply(lambda r: safe_pct(r["SGM_FC"], r["NS_FC"]), axis=1)
        cmp = cmp.sort_values("NS_ACT", ascending=False)

        show_cmp = cmp[["Product Line", "NS_ACT", "NS_FC", "GAP", "VAR_%",
                        "SGM%_ACT", "SGM%_FC"]].copy()
        show_cmp["SGM_GAP"] = show_cmp["SGM%_ACT"] - show_cmp["SGM%_FC"]
        show_cmp.columns = ["Product Line", "NS Actual", f"NS {sel_round}", "Gap", "Var %",
                            "SGM% Act", "SGM% FC", "SGM% gap"]

        # ----- Dong Grand Total -----
        t_act = cmp["NS_ACT"].sum()
        t_fc  = cmp["NS_FC"].sum()
        t_sgm_act = cmp["SGM_ACT"].sum()
        t_sgm_fc  = cmp["SGM_FC"].sum()
        gt_sgm_act = safe_pct(t_sgm_act, t_act)
        gt_sgm_fc  = safe_pct(t_sgm_fc, t_fc)
        grand = {
            "Product Line": "GRAND TOTAL",
            "NS Actual": t_act,
            f"NS {sel_round}": t_fc,
            "Gap": t_act - t_fc,
            "Var %": safe_pct(t_act - t_fc, t_fc),
            "SGM% Act": gt_sgm_act,
            "SGM% FC": gt_sgm_fc,
            "SGM% gap": gt_sgm_act - gt_sgm_fc,
        }
        show_cmp = pd.concat([show_cmp, pd.DataFrame([grand])], ignore_index=True)

        def color_pn(v):
            try:
                v = float(v)
            except (TypeError, ValueError):
                return ""
            if v > 0: return "color: #16a34a; font-weight: 700;"
            if v < 0: return "color: #dc2626; font-weight: 700;"
            return ""

        def bold_total(row):
            if str(row["Product Line"]).strip().upper() == "GRAND TOTAL":
                return ["font-weight: 800; border-top: 2px solid #94a3b8;"] * len(row)
            return [""] * len(row)

        # ===== Bo tri 2 cot: bang trai, chart Gap ngang phai =====
        col_tbl, col_chart = st.columns([1.25, 1])

        with col_tbl:
            st.dataframe(
                show_cmp.style.format({
                    "NS Actual": "{:,.0f}", f"NS {sel_round}": "{:,.0f}", "Gap": "{:,.0f}",
                    "Var %": "{:+.1f}%", "SGM% Act": "{:.2f}%", "SGM% FC": "{:.2f}%",
                    "SGM% gap": "{:+.2f}",
                }).apply(bold_total, axis=1)
                  .map(color_pn, subset=["Gap", "Var %", "SGM% gap"]),
                use_container_width=True, hide_index=True, height=430
            )

        with col_chart:
            gap_df = cmp.sort_values("GAP")   # am truoc, duong sau
            bar_colors = [COLORS["POS"] if g >= 0 else COLORS["NEG"] for g in gap_df["GAP"]]
            fig_gap = go.Figure(go.Bar(
                y=gap_df["Product Line"], x=gap_df["GAP"], orientation="h",
                marker_color=bar_colors,
                text=[f"{g/1e9:+.1f}B" for g in gap_df["GAP"]],
                textposition="outside", cliponaxis=False,
            ))
            fig_gap.add_vline(x=0, line_color="#94a3b8", line_width=1)
            fig_gap.update_layout(
                template="seb_dark", height=430,
                margin=dict(t=40, b=20, l=10, r=60),
                xaxis_title="Gap vs Forecast (Actual − F5+7)",
                showlegend=False,
                title=f"Gap vs {sel_round} ({sel_m}) by Product Line",
            )
            st.plotly_chart(fig_gap, use_container_width=True)

        st.caption("Luu y: Forecast F5+7 khong chia theo MLA, nen phan so sanh nay gom ve Product Line.  "
                   "Chart Gap: xanh = vuot forecast, do = hut forecast.")

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
