import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.io as pio

# ==================================================
# PLOTLY THEME (dong bo voi cac trang khac)
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
</style>
""", unsafe_allow_html=True)

# ==================================================
# CONSTANTS
# ==================================================

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ACT_FILE   = os.path.join(BASE_DIR, "data_cache.parquet")
FC_FILE    = os.path.join(BASE_DIR, "forecast_cache.parquet")

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

COLORS = {"ACT": "#2563eb", "FC": "#9ca3af", "POS": "#16a34a", "NEG": "#dc2626"}

# ==================================================
# BANG ANH XA TEN FAMILY LEVEL 2
# File Actual dung ten viet tat, file Forecast dung ten day du.
# Key = ten trong ACTUAL (chu hoa)  ->  Value = ten trong FORECAST (chu hoa)
# Neu sau nay co ten moi bi lech, chi can them 1 dong vao day.
# ==================================================

FAMILY_MAP = {
    "CANISTER VAC CL":      "CANISTER VACUUM CLEANER",
    "CONVIVIAL COOKG":      "CONVIVIAL COOKING",
    "DAILY ING.PROCESSOR":  "DAILY INGREDIENTS PROCESSOR",
    "ELECT.PRES.CK&MULTI":  "ELECTRIC PRESSURE COOKER & MULTICOOKER",
    "HANDSTICK VAC.CLEAN.": "HANDSTICK VACUUM CLEANER",
    "P&P FIXED HANDLES AL": "P&P FIXED HANDLES ALUMINIUM",
    "P&P FIXED HANDLES OT": "P&P FIXED HANDLES OTHER",
    "P&P FIXED HANDLES ST": "P&P FIXED HANDLES STAINLESS STEEL",
    "P&P STACKABLES ALU":   "P&P STACKABLES ALUMINIUM",
    "P&P STACKABLES ST":    "P&P STACKABLES STAINLESS STEEL",
    "PRESSURE COOKER":      "PRESSURE COOKER",
    "SP PART & OTHER":      "SPARE PARTS & OTHER",
    "TOOL, GAD&MAN.FD PRE": "TOOLS, GADGETS & MANUAL FOOD PREPARATION",
}


def norm_family(s):
    """Chuan hoa ten Family: chu hoa, bo khoang trang thua, roi ap bang anh xa."""
    s = " ".join(str(s).strip().upper().split())
    return FAMILY_MAP.get(s, s)


def safe_pct(num, den):
    return num / den * 100 if den else 0


def fmt_abbr(v):
    v = float(v)
    if abs(v) >= 1e9: return f"{v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"{v/1e6:.1f}M"
    return f"{v:,.0f}"


def fmt_full(v):
    return f"{float(v):,.0f}"


# ==================================================
# LOAD DATA
# ==================================================

@st.cache_data(show_spinner="Loading data...")
def load_parquet(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)


df_act = load_parquet(ACT_FILE)
df_fc  = load_parquet(FC_FILE)

if df_fc.empty:
    st.error("Chua co file forecast_cache.parquet. Vui long chay convert_forecast.py truoc.")
    st.stop()

if df_act.empty:
    st.error("Chua co file data_cache.parquet. Vui long chay convert_to_parquet.py truoc.")
    st.stop()

if "Family Level 2" not in df_act.columns:
    st.error("File data_cache.parquet khong co cot 'Family Level 2'.")
    st.stop()

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.header("🔮 Forecast Filters")

fc_rounds = sorted(df_fc["Forecast"].dropna().unique())
sel_fc = st.sidebar.selectbox("Forecast round", fc_rounds,
                              help="Chon vong forecast de so sanh voi Actual")

months_fc  = [m for m in MONTH_ORDER if m in df_fc["MONTH"].unique()]
months_act = [m for m in MONTH_ORDER if m in df_act["MONTH"].dropna().unique()]
month_opts = ["YTD (tat ca thang co Actual)"] + months_act

sel_month = st.sidebar.selectbox("Month", month_opts)

st.sidebar.markdown("---")

pl_opts = ["All"] + sorted(df_fc["Product Line"].dropna().unique())
sel_pl = st.sidebar.selectbox("Product Line", pl_opts)

# ==================================================
# CHUAN BI DU LIEU
# ==================================================

# --- Actual ---
a = df_act.copy()
has_sgm_act = "SGM_ACT" in a.columns

if sel_month.startswith("YTD"):
    months_used = months_act
else:
    months_used = [sel_month]

a = a[a["MONTH"].isin(months_used)]

agg_act = {"NS_ACT": "sum"}
if has_sgm_act:
    agg_act["SGM_ACT"] = "sum"

act_fl2 = (a.groupby("Family Level 2", as_index=False, observed=True).agg(agg_act))
act_fl2["KEY"] = act_fl2["Family Level 2"].map(norm_family)
# Gop lai phong truong hop nhieu ten viet tat cung tro ve 1 ten chuan
act_fl2 = act_fl2.groupby("KEY", as_index=False, observed=True).agg(
    {c: "sum" for c in agg_act}
)

# --- Forecast ---
f = df_fc[df_fc["Forecast"] == sel_fc].copy()
f = f[f["MONTH"].isin(months_used)]

if sel_pl != "All":
    f = f[f["Product Line"] == sel_pl]

fc_fl2 = (f.groupby(["Family Level 2", "Product Line"], as_index=False, observed=True)
          .agg(NS_FC=("NS_FC", "sum"), SGM_FC=("SGM_FC", "sum")))
fc_fl2["KEY"] = fc_fl2["Family Level 2"].map(norm_family)

# --- Ghep theo KEY da chuan hoa ---
cmp_df = fc_fl2.merge(act_fl2, on="KEY", how="outer")

cmp_df["Family Level 2"] = cmp_df["Family Level 2"].fillna(cmp_df["KEY"])
cmp_df["Product Line"] = cmp_df["Product Line"].fillna("(khong co trong forecast)")

for c in ["NS_FC", "SGM_FC", "NS_ACT"] + (["SGM_ACT"] if has_sgm_act else []):
    if c in cmp_df.columns:
        cmp_df[c] = pd.to_numeric(cmp_df[c], errors="coerce").fillna(0)
    else:
        cmp_df[c] = 0

if sel_pl != "All":
    cmp_df = cmp_df[cmp_df["Product Line"] == sel_pl]

cmp_df = cmp_df[(cmp_df["NS_FC"] != 0) | (cmp_df["NS_ACT"] != 0)]

if cmp_df.empty:
    st.warning("Khong co du lieu khop giua Actual va Forecast voi bo loc hien tai.")
    st.stop()

cmp_df["GAP"] = cmp_df["NS_ACT"] - cmp_df["NS_FC"]
cmp_df["VAR_%"] = cmp_df.apply(lambda r: safe_pct(r["NS_ACT"] - r["NS_FC"], r["NS_FC"]), axis=1)
cmp_df["SGM%_ACT"] = cmp_df.apply(lambda r: safe_pct(r["SGM_ACT"], r["NS_ACT"]), axis=1)
cmp_df["SGM%_FC"]  = cmp_df.apply(lambda r: safe_pct(r["SGM_FC"], r["NS_FC"]), axis=1)

# --- Canh bao cac Family chi co o 1 ben (co the do ten bi lech) ---
only_act = cmp_df[(cmp_df["NS_FC"] == 0) & (cmp_df["NS_ACT"] != 0)]
only_fc  = cmp_df[(cmp_df["NS_ACT"] == 0) & (cmp_df["NS_FC"] != 0)]

if not only_act.empty or not only_fc.empty:
    with st.expander(
        f"⚠️ {len(only_act) + len(only_fc)} Family chỉ xuất hiện ở 1 bên "
        "(bán ngoài kế hoạch, chưa bán, hoặc tên bị lệch)", expanded=False
    ):
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Có Actual nhưng không có Forecast**")
            if only_act.empty:
                st.caption("Không có.")
            else:
                st.dataframe(
                    only_act[["Family Level 2", "NS_ACT"]]
                    .sort_values("NS_ACT", ascending=False)
                    .rename(columns={"NS_ACT": "NS Actual"})
                    .style.format({"NS Actual": "{:,.0f}"}),
                    use_container_width=True, hide_index=True
                )
        with cc2:
            st.markdown("**Có Forecast nhưng không có Actual**")
            if only_fc.empty:
                st.caption("Không có.")
            else:
                st.dataframe(
                    only_fc[["Family Level 2", "NS_FC"]]
                    .sort_values("NS_FC", ascending=False)
                    .rename(columns={"NS_FC": "NS Forecast"})
                    .style.format({"NS Forecast": "{:,.0f}"}),
                    use_container_width=True, hide_index=True
                )
        st.caption(
            "Nếu thấy 2 dòng ở 2 bên rõ ràng là **cùng một nhóm nhưng tên viết khác nhau**, "
            "hãy báo để thêm vào bảng FAMILY_MAP trong file page_forecast.py."
        )

# ==================================================
# HERO + KPI
# ==================================================

tot_ns_act = cmp_df["NS_ACT"].sum()
tot_ns_fc  = cmp_df["NS_FC"].sum()
tot_sgm_act = cmp_df["SGM_ACT"].sum()
tot_sgm_fc  = cmp_df["SGM_FC"].sum()

ach = safe_pct(tot_ns_act, tot_ns_fc)
sgm_pct_act = safe_pct(tot_sgm_act, tot_ns_act)
sgm_pct_fc  = safe_pct(tot_sgm_fc, tot_ns_fc)

period_txt = "YTD" if sel_month.startswith("YTD") else sel_month

st.markdown(f"""
<div class="hero">
  <div class="hero-title">🔮 Forecast vs Actual</div>
  <div class="hero-sub">Round: {sel_fc}  •  Period: {period_txt}  •  Product Line: {sel_pl}</div>
  <div class="hero-kpis">
    <div class="hero-tile"><div class="lbl">NS Actual</div><div class="val">{fmt_full(tot_ns_act)}</div><div class="sub">VND</div></div>
    <div class="hero-tile"><div class="lbl">NS Forecast</div><div class="val">{fmt_full(tot_ns_fc)}</div><div class="sub">{sel_fc}</div></div>
    <div class="hero-tile"><div class="lbl">Achievement</div><div class="val">{ach:.1f}%</div><div class="sub">{fmt_abbr(tot_ns_act - tot_ns_fc)} gap</div></div>
    <div class="hero-tile"><div class="lbl">SGM% Act vs FC</div><div class="val">{sgm_pct_act:.1f}%</div><div class="sub">FC {sgm_pct_fc:.1f}%  ({sgm_pct_act - sgm_pct_fc:+.1f} pp)</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ==================================================
# TABS
# ==================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 By Family Level 2", "📦 By Product Line",
    "🔬 SGM% Gap Bridge", "📅 Full Year & YTG", "📋 Detail Table"
])

fmt_tbl = {
    "NS Actual": "{:,.0f}", "NS Forecast": "{:,.0f}", "Gap": "{:,.0f}",
    "Var %": "{:+.1f}%", "SGM% Act": "{:.2f}%", "SGM% FC": "{:.2f}%",
    "SGM% gap": "{:+.2f}",
}


def color_pos_neg(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    if v > 0:
        return "color: #16a34a; font-weight: 700;"
    if v < 0:
        return "color: #dc2626; font-weight: 700;"
    return ""


# ---------- Tab 1: By Family Level 2 ----------
with tab1:
    top_n = st.slider("So Family hien thi (theo gap lon nhat):", 5, 40, 15, key="fc_fl2_top")

    d = cmp_df.reindex(cmp_df["GAP"].abs().sort_values(ascending=False).index).head(top_n)
    d = d.sort_values("GAP")

    fig = go.Figure()
    fig.add_bar(y=d["Family Level 2"], x=d["NS_FC"], orientation="h",
                name=f"Forecast {sel_fc}", marker_color=COLORS["FC"])
    fig.add_bar(y=d["Family Level 2"], x=d["NS_ACT"], orientation="h",
                name="Actual", marker_color=COLORS["ACT"])
    fig.update_layout(barmode="group", template="seb_dark",
                      height=max(420, top_n * 34),
                      margin=dict(t=30, b=20, l=10, r=30),
                      xaxis_title="Net Sales",
                      legend=dict(orientation="h", y=-0.08),
                      title=f"Actual vs {sel_fc} — Net Sales by Family Level 2")
    st.plotly_chart(fig, use_container_width=True)

    show = d[["Family Level 2", "Product Line", "NS_ACT", "NS_FC", "GAP", "VAR_%",
              "SGM%_ACT", "SGM%_FC"]].copy()
    show["SGM_GAP"] = show["SGM%_ACT"] - show["SGM%_FC"]
    show.columns = ["Family Level 2", "Product Line", "NS Actual", "NS Forecast",
                    "Gap", "Var %", "SGM% Act", "SGM% FC", "SGM% gap"]
    st.dataframe(
        show.sort_values("Gap").style.format(fmt_tbl)
            .map(color_pos_neg, subset=["Gap", "Var %", "SGM% gap"]),
        use_container_width=True, hide_index=True, height=460
    )

# ---------- Tab 2: By Product Line ----------
with tab2:
    by_pl = (cmp_df.groupby("Product Line", as_index=False, observed=True)
             .agg(NS_ACT=("NS_ACT", "sum"), NS_FC=("NS_FC", "sum"),
                  SGM_ACT=("SGM_ACT", "sum"), SGM_FC=("SGM_FC", "sum")))
    by_pl["GAP"] = by_pl["NS_ACT"] - by_pl["NS_FC"]
    by_pl["VAR_%"] = by_pl.apply(lambda r: safe_pct(r["NS_ACT"] - r["NS_FC"], r["NS_FC"]), axis=1)
    by_pl["SGM%_ACT"] = by_pl.apply(lambda r: safe_pct(r["SGM_ACT"], r["NS_ACT"]), axis=1)
    by_pl["SGM%_FC"]  = by_pl.apply(lambda r: safe_pct(r["SGM_FC"], r["NS_FC"]), axis=1)
    by_pl = by_pl.sort_values("NS_ACT", ascending=False)

    fig_pl = go.Figure()
    fig_pl.add_bar(x=by_pl["Product Line"], y=by_pl["NS_FC"],
                   name=f"Forecast {sel_fc}", marker_color=COLORS["FC"])
    fig_pl.add_bar(x=by_pl["Product Line"], y=by_pl["NS_ACT"],
                   name="Actual", marker_color=COLORS["ACT"])
    fig_pl.update_layout(barmode="group", template="seb_dark", height=460,
                         margin=dict(t=30, b=110),
                         yaxis_title="Net Sales", xaxis_tickangle=-30,
                         legend=dict(orientation="h", y=-0.35),
                         title=f"Actual vs {sel_fc} — Net Sales by Product Line")
    st.plotly_chart(fig_pl, use_container_width=True)

    show_pl = by_pl[["Product Line", "NS_ACT", "NS_FC", "GAP", "VAR_%",
                     "SGM%_ACT", "SGM%_FC"]].copy()
    show_pl["SGM_GAP"] = show_pl["SGM%_ACT"] - show_pl["SGM%_FC"]
    show_pl.columns = ["Product Line", "NS Actual", "NS Forecast", "Gap", "Var %",
                       "SGM% Act", "SGM% FC", "SGM% gap"]
    st.dataframe(
        show_pl.style.format(fmt_tbl)
               .map(color_pos_neg, subset=["Gap", "Var %", "SGM% gap"]),
        use_container_width=True, hide_index=True
    )

# ---------- Tab 3: SGM% Gap Bridge ----------
with tab3:
    st.subheader(f"SGM% Gap Bridge — Actual vs {sel_fc}")
    st.caption(
        "Tach chenh lech SGM% tong thanh 2 nguyen nhan:  "
        "**Mix effect** = do ty trong doanh so dich chuyen giua cac Family  •  "
        "**SGM% effect** = do bien cua tung Family thay doi.  Don vi: diem phan tram (pp)."
    )

    br = cmp_df[["Family Level 2", "NS_ACT", "NS_FC", "SGM_ACT", "SGM_FC"]].copy()

    t_act, t_fc = br["NS_ACT"].sum(), br["NS_FC"].sum()
    br["SGM%_ACT"] = br.apply(lambda r: safe_pct(r["SGM_ACT"], r["NS_ACT"]), axis=1)
    br["SGM%_FC"]  = br.apply(lambda r: safe_pct(r["SGM_FC"], r["NS_FC"]), axis=1)
    br["MIX_ACT"] = br["NS_ACT"] / t_act * 100 if t_act else 0
    br["MIX_FC"]  = br["NS_FC"] / t_fc * 100 if t_fc else 0

    sgm_fc_total  = safe_pct(br["SGM_FC"].sum(), t_fc)
    sgm_act_total = safe_pct(br["SGM_ACT"].sum(), t_act)

    br["MIX_EFFECT"] = (br["MIX_ACT"] - br["MIX_FC"]) * (br["SGM%_FC"] - sgm_fc_total) / 100
    br["SGM_EFFECT"] = (br["SGM%_ACT"] - br["SGM%_FC"]) * br["MIX_ACT"] / 100
    br["TOTAL_IMPACT"] = br["MIX_EFFECT"] + br["SGM_EFFECT"]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("SGM% Actual", f"{sgm_act_total:.2f}%")
    k2.metric(f"SGM% {sel_fc}", f"{sgm_fc_total:.2f}%")
    k3.metric("Gap", f"{sgm_act_total - sgm_fc_total:+.2f} pp")
    k4.metric("Mix / SGM% effect",
              f"{br['MIX_EFFECT'].sum():+.2f} / {br['SGM_EFFECT'].sum():+.2f} pp")

    top_br = st.slider("So Family hien thi tren waterfall:", 5, 30, 12, key="fc_bridge_top")
    br_rank = br.reindex(br["TOTAL_IMPACT"].abs().sort_values(ascending=False).index)
    top_items = br_rank.head(top_br).sort_values("TOTAL_IMPACT")
    others = br_rank.iloc[top_br:]["TOTAL_IMPACT"].sum()

    labels = [f"SGM% {sel_fc}"] + top_items["Family Level 2"].tolist()
    values = [sgm_fc_total] + top_items["TOTAL_IMPACT"].tolist()
    measures = ["absolute"] + ["relative"] * len(top_items)

    if abs(others) > 1e-9:
        labels.append("Others"); values.append(others); measures.append("relative")

    labels.append("SGM% Actual"); values.append(sgm_act_total); measures.append("total")

    fig_br = go.Figure(go.Waterfall(
        orientation="v", measure=measures, x=labels, y=values,
        text=[f"{v:+.2f}" if m == "relative" else f"{v:.2f}%"
              for v, m in zip(values, measures)],
        textposition="outside",
        connector=dict(line=dict(color="#9ca3af")),
        increasing=dict(marker=dict(color=COLORS["POS"])),
        decreasing=dict(marker=dict(color=COLORS["NEG"])),
        totals=dict(marker=dict(color=COLORS["ACT"])),
    ))
    fig_br.update_layout(template="seb_dark", height=520,
                         margin=dict(t=30, b=150), yaxis_title="SGM% (pp)",
                         xaxis_tickangle=-40, showlegend=False)
    st.plotly_chart(fig_br, use_container_width=True)

    show_br = br[["Family Level 2", "NS_ACT", "SGM%_ACT", "MIX_ACT",
                  "NS_FC", "SGM%_FC", "MIX_FC",
                  "MIX_EFFECT", "SGM_EFFECT", "TOTAL_IMPACT"]].sort_values("TOTAL_IMPACT")
    show_br.columns = ["Family Level 2", "NS Actual", "SGM% Act", "Mix% Act",
                       "NS Forecast", "SGM% FC", "Mix% FC",
                       "Mix effect", "SGM% effect", "Total impact"]
    st.dataframe(
        show_br.style.format({
            "NS Actual": "{:,.0f}", "NS Forecast": "{:,.0f}",
            "SGM% Act": "{:.2f}%", "SGM% FC": "{:.2f}%",
            "Mix% Act": "{:.2f}%", "Mix% FC": "{:.2f}%",
            "Mix effect": "{:+.3f}", "SGM% effect": "{:+.3f}", "Total impact": "{:+.3f}",
        }).map(color_pos_neg, subset=["Mix effect", "SGM% effect", "Total impact"]),
        use_container_width=True, hide_index=True, height=460
    )

# ---------- Tab 4: Full Year & YTG ----------
with tab4:
    st.subheader(f"Full Year outlook — {sel_fc}")
    st.caption(
        "**YTD** = cac thang da co Actual  •  **YTG (Year To Go)** = cac thang con lai theo forecast  •  "
        "**Full Year** = YTD Actual + YTG Forecast.  Bo loc thang o sidebar khong anh huong tab nay."
    )

    # --- Du lieu ca nam cua vong forecast dang chon (khong loc theo thang) ---
    fy = df_fc[df_fc["Forecast"] == sel_fc].copy()
    if sel_pl != "All":
        fy = fy[fy["Product Line"] == sel_pl]

    fc_month = (fy.groupby("MONTH", as_index=False, observed=True)
                .agg(NS_FC=("NS_FC", "sum"), SGM_FC=("SGM_FC", "sum")))

    # --- Actual theo thang (khong loc theo thang) ---
    aa = df_act.copy()
    if sel_pl != "All" and "Product Line" in aa.columns:
        aa = aa[aa["Product Line"].astype(str).str.strip().str.upper()
                == str(sel_pl).strip().upper()]

    agg_m = {"NS_ACT": "sum"}
    if has_sgm_act:
        agg_m["SGM_ACT"] = "sum"
    act_month = aa.groupby("MONTH", as_index=False, observed=True).agg(agg_m)
    if not has_sgm_act:
        act_month["SGM_ACT"] = 0

    # --- Ghep theo thang, giu dung thu tu 12 thang ---
    base = pd.DataFrame({"MONTH": MONTH_ORDER})
    m = (base.merge(fc_month, on="MONTH", how="left")
             .merge(act_month, on="MONTH", how="left"))
    for c in ["NS_FC", "SGM_FC", "NS_ACT", "SGM_ACT"]:
        m[c] = pd.to_numeric(m[c], errors="coerce").fillna(0)

    # Thang nao co Actual thi tinh la YTD, con lai la YTG
    m["HAS_ACT"] = m["MONTH"].isin(months_act) & (m["NS_ACT"] != 0)
    m["NS_FY"]  = m.apply(lambda r: r["NS_ACT"]  if r["HAS_ACT"] else r["NS_FC"],  axis=1)
    m["SGM_FY"] = m.apply(lambda r: r["SGM_ACT"] if r["HAS_ACT"] else r["SGM_FC"], axis=1)
    m["SGM%_ACT"] = m.apply(lambda r: safe_pct(r["SGM_ACT"], r["NS_ACT"]), axis=1)
    m["SGM%_FC"]  = m.apply(lambda r: safe_pct(r["SGM_FC"], r["NS_FC"]), axis=1)

    ytd = m[m["HAS_ACT"]]
    ytg = m[~m["HAS_ACT"]]

    ns_ytd, sgm_ytd = ytd["NS_ACT"].sum(), ytd["SGM_ACT"].sum()
    ns_ytg, sgm_ytg = ytg["NS_FC"].sum(),  ytg["SGM_FC"].sum()
    ns_fy,  sgm_fy  = ns_ytd + ns_ytg,     sgm_ytd + sgm_ytg
    ns_fc_fy, sgm_fc_fy = m["NS_FC"].sum(), m["SGM_FC"].sum()

    # --- KPI ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"YTD Actual ({len(ytd)} thang)", fmt_abbr(ns_ytd),
              f"SGM% {safe_pct(sgm_ytd, ns_ytd):.1f}%")
    c2.metric(f"YTG Forecast ({len(ytg)} thang)", fmt_abbr(ns_ytg),
              f"SGM% {safe_pct(sgm_ytg, ns_ytg):.1f}%")
    c3.metric("Full Year outlook", fmt_abbr(ns_fy),
              f"SGM% {safe_pct(sgm_fy, ns_fy):.1f}%")
    c4.metric(f"FY {sel_fc} (100% forecast)", fmt_abbr(ns_fc_fy),
              f"{ns_fy - ns_fc_fy:+,.0f} vs FC", delta_color="normal")

    st.markdown("")

    # --- Chart: cot theo thang + duong SGM% ---
    fig_fy = go.Figure()

    fig_fy.add_bar(
        x=ytd["MONTH"], y=ytd["NS_ACT"], name="Actual (YTD)",
        marker_color=COLORS["ACT"],
        text=[fmt_abbr(v) for v in ytd["NS_ACT"]], textposition="outside",
    )
    fig_fy.add_bar(
        x=ytg["MONTH"], y=ytg["NS_FC"], name=f"Forecast (YTG) — {sel_fc}",
        marker_color=COLORS["FC"],
        text=[fmt_abbr(v) for v in ytg["NS_FC"]], textposition="outside",
    )
    # Duong SGM%: dung Actual cho YTD, Forecast cho YTG
    sgm_line = m.apply(
        lambda r: r["SGM%_ACT"] if r["HAS_ACT"] else r["SGM%_FC"], axis=1
    )
    fig_fy.add_scatter(
        x=m["MONTH"], y=sgm_line, name="SGM%", yaxis="y2",
        mode="lines+markers+text",
        text=[f"{v:.1f}%" for v in sgm_line], textposition="top center",
        line=dict(color="#22d3ee", width=2),
    )
    fig_fy.update_layout(
        template="seb_dark", height=500, barmode="group",
        margin=dict(t=40, b=60),
        xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER),
        yaxis=dict(title="Net Sales"),
        yaxis2=dict(title="SGM%", overlaying="y", side="right",
                    ticksuffix="%", showgrid=False),
        legend=dict(orientation="h", y=-0.15),
        title=f"Net Sales & SGM% theo thang — YTD Actual + YTG {sel_fc}",
    )
    st.plotly_chart(fig_fy, use_container_width=True)

    # --- Bang theo thang ---
    show_m = m[["MONTH", "NS_ACT", "SGM%_ACT", "NS_FC", "SGM%_FC"]].copy()
    show_m["GAP"] = show_m["NS_ACT"] - show_m["NS_FC"]
    show_m["Type"] = m["HAS_ACT"].map({True: "YTD (Actual)", False: "YTG (Forecast)"})
    show_m = show_m[["MONTH", "Type", "NS_ACT", "SGM%_ACT", "NS_FC", "SGM%_FC", "GAP"]]
    show_m.columns = ["Month", "Type", "NS Actual", "SGM% Act",
                      "NS Forecast", "SGM% FC", "Gap"]
    st.dataframe(
        show_m.style.format({
            "NS Actual": "{:,.0f}", "NS Forecast": "{:,.0f}", "Gap": "{:,.0f}",
            "SGM% Act": "{:.2f}%", "SGM% FC": "{:.2f}%",
        }).map(color_pos_neg, subset=["Gap"]),
        use_container_width=True, hide_index=True, height=460
    )

    # --- Goc nhin YTG: can dat bao nhieu ---
    st.markdown("---")
    st.markdown("#### 🎯 YTG cần đạt bao nhiêu?")

    y1, y2, y3 = st.columns(3)
    y1.metric("NS còn phải làm (YTG)", fmt_full(ns_ytg),
              f"{len(ytg)} tháng còn lại")
    y2.metric("SGM% YTG phải đạt", f"{safe_pct(sgm_ytg, ns_ytg):.2f}%",
              f"{safe_pct(sgm_ytg, ns_ytg) - safe_pct(sgm_ytd, ns_ytd):+.2f} pp vs YTD")
    y3.metric("SGM value YTG", fmt_full(sgm_ytg))

    if len(ytg):
        avg_ytg = ns_ytg / len(ytg)
        avg_ytd = ns_ytd / len(ytd) if len(ytd) else 0
        st.caption(
            f"Trung bình mỗi tháng YTG cần **{fmt_full(avg_ytg)}** "
            f"(YTD đang trung bình {fmt_full(avg_ytd)} / tháng — "
            f"chênh {safe_pct(avg_ytg - avg_ytd, avg_ytd):+.1f}%)."
        )
    else:
        st.caption("Đã có Actual cho toàn bộ 12 tháng — không còn YTG.")

# ---------- Tab 5: Detail ----------
with tab5:
    st.subheader(f"Chi tiet ({len(cmp_df):,} dong) — Actual vs {sel_fc}")
    det = cmp_df[["Product Line", "Family Level 2", "NS_ACT", "NS_FC", "GAP", "VAR_%",
                  "SGM_ACT", "SGM_FC", "SGM%_ACT", "SGM%_FC"]].copy()
    det["SGM_GAP"] = det["SGM%_ACT"] - det["SGM%_FC"]
    det.columns = ["Product Line", "Family Level 2", "NS Actual", "NS Forecast",
                   "Gap", "Var %", "SGM Actual", "SGM Forecast",
                   "SGM% Act", "SGM% FC", "SGM% gap"]
    st.dataframe(
        det.sort_values("Gap").style.format({
            "NS Actual": "{:,.0f}", "NS Forecast": "{:,.0f}", "Gap": "{:,.0f}",
            "Var %": "{:+.1f}%", "SGM Actual": "{:,.0f}", "SGM Forecast": "{:,.0f}",
            "SGM% Act": "{:.2f}%", "SGM% FC": "{:.2f}%", "SGM% gap": "{:+.2f}",
        }).map(color_pos_neg, subset=["Gap", "Var %", "SGM% gap"]),
        use_container_width=True, hide_index=True, height=600
    )
