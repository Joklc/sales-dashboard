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
    [data-testid="stAppViewContainer"], .stApp { background-color: #e2e8f0; }
    .hero { background: transparent; border-radius: 18px; padding: 18px 6px 16px 6px; margin-bottom: 14px; }
    .hero-title { color: #1e293b; font-size: 28px; font-weight: 800; margin: 0; line-height: 1.1; }
    .hero-sub   { color: #64748b; font-size: 13px; margin: 6px 0 18px 0; }
    .hero-kpis  { display: flex; gap: 14px; flex-wrap: wrap; }
    .hero-tile  { flex: 1; min-width: 150px; background: #3b82f6;
        border: 1px solid #3b82f6; border-radius: 12px; padding: 14px 16px; }
    .hero-tile .lbl { color: #dbe7ff; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
    .hero-tile .val { color: #ffffff; font-size: 22px; font-weight: 800; margin-top: 4px; }
    .hero-tile .sub { color: #b9d0ff; font-size: 11px; margin-top: 2px; }
    [data-testid="stDataFrame"] thead tr th {
        background-color: #475569 !important; color: #ffffff !important; font-weight: 700 !important; }
    [data-testid="stDataFrame"] [role="columnheader"] {
        background-color: #475569 !important; color: #ffffff !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

COLORS = {"ACT": "#3b82f6", "BUD": "#9ca3af", "FC": "#f59e0b",
          "POS": "#16a34a", "NEG": "#dc2626"}


def safe_pct(n, d):
    return (n / d * 100) if d else 0


def fmt_full(v):
    return f"{v:,.0f}"


def fmt_abbr(v):
    a = abs(v)
    if a >= 1e9:
        return f"{v/1e9:.2f}B"
    if a >= 1e6:
        return f"{v/1e6:.1f}M"
    if a >= 1e3:
        return f"{v/1e3:.0f}K"
    return f"{v:,.0f}"


# ==================================================
# LOAD DATA
# ==================================================
OPEX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opex_cache.parquet")
SALES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache.parquet")

# Map ten thang (Sales) <-> so thang (OPEX Period)
MONTH_TO_NUM = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05",
                "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10",
                "Nov": "11", "Dec": "12"}
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@st.cache_data(show_spinner="Loading OPEX data...")
def load_opex(path):
    return pd.read_parquet(path)


if not os.path.exists(OPEX_FILE):
    st.error("Chua co opex_cache.parquet. Chay convert_opex.py truoc.")
    st.stop()

try:
    df = load_opex(OPEX_FILE)
except Exception as e:
    st.error(f"Error reading OPEX data: {e}")
    st.stop()

# Loai GPS L2 = S2520 (Non contributive services / Management fee) khoi TOAN BO trang.
# Cac dong nay khong tinh vao Primary Contribution.
if "GPS L2" in df.columns:
    df = df[df["GPS L2"].astype(str).str.strip().str.upper() != "S2520"]

# ==================================================
# SIDEBAR FILTERS
# ==================================================
st.sidebar.header("🔍 OPEX Filters")

def ms(label, col):
    """Multiselect cho 1 cot; tra ve list gia tri chon (rong = tat ca)."""
    if col not in df.columns:
        return []
    opts = sorted([x for x in df[col].dropna().astype(str).unique() if x != ""])
    return st.sidebar.multiselect(label, opts, default=[])

f_le      = ms("LE", "LE")
f_period  = ms("Period", "Period")
f_pnl     = ms("PnL Line", "PnL Line")
f_subpnl  = ms("sub_PnL Line", "sub_PnL Line")
f_nature  = ms("NATURE NAME", "NATURE NAME")
f_nat2    = ms("NATURE L2 NAME", "NATURE L2 NAME")
f_cccode  = ms("Cost Center Code", "Cost Center Code")
f_cc      = ms("Cost Center Name", "Cost Center Name")
f_me      = ms("ME", "ME")


def apply_filter(data):
    d = data.copy()
    for col, sel in [("LE", f_le), ("Period", f_period), ("PnL Line", f_pnl),
                     ("sub_PnL Line", f_subpnl), ("NATURE NAME", f_nature),
                     ("NATURE L2 NAME", f_nat2),
                     ("Cost Center Code", f_cccode), ("Cost Center Name", f_cc),
                     ("ME", f_me)]:
        if sel and col in d.columns:
            d = d[d[col].astype(str).isin(sel)]
    return d


dff = apply_filter(df)

# Tach 3 Type de so sanh
act = dff[dff["Type"] == "ACT_26"]["Amount"].sum()
bud = dff[dff["Type"] == "BUD_26"]["Amount"].sum()
fc  = dff[dff["Type"] == "F5+7"]["Amount"].sum()

var_bud = act - bud
var_pct = safe_pct(act - bud, bud)

# ==================================================
# HERO + KPI
# ==================================================
st.markdown(f"""
<div class="hero">
  <div class="hero-title">💵 OPEX tracking</div>
  <div class="hero-sub">Actual 2026 vs Budget 2026 vs Forecast F5+7 · Amount giu nguyen dau (chi phi = am)</div>
  <div class="hero-kpis">
    <div class="hero-tile"><div class="lbl">Actual 2026</div><div class="val">{fmt_full(act)}</div><div class="sub">ACT_26</div></div>
    <div class="hero-tile"><div class="lbl">Budget 2026</div><div class="val">{fmt_full(bud)}</div><div class="sub">BUD_26</div></div>
    <div class="hero-tile"><div class="lbl">Forecast F5+7</div><div class="val">{fmt_full(fc)}</div><div class="sub">F5+7</div></div>
    <div class="hero-tile"><div class="lbl">Var vs Budget</div><div class="val">{fmt_full(var_bud)}</div><div class="sub">{var_pct:+.1f}% vs BUD</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

st.caption(f"Da loc: {len(dff):,} dong / {len(df):,} dong tong.")

tab1, tab2, tab5, tab3 = st.tabs(["📊 By PnL Line", "🏷️ By Nature",
                                  "🎯 Primary Contribution", "📋 Detail"])


def compare_by(dimension, months=None):
    """Gom Amount theo dimension x Type, tra ve bang wide ACT/BUD/FC.
    months: neu co, chi lay cac Period 2026-MM tuong ung."""
    src = dff[dff["Type"].isin(["ACT_26", "BUD_26", "F5+7"])]
    if months:
        periods = [f"2026-{m}" for m in months]
        src = src[src["Period"].isin(periods)]
    g = (src.groupby([dimension, "Type"], observed=True)["Amount"].sum().reset_index())
    if g.empty:
        return pd.DataFrame()
    w = g.pivot(index=dimension, columns="Type", values="Amount").fillna(0)
    for c in ["ACT_26", "BUD_26", "F5+7"]:
        if c not in w.columns:
            w[c] = 0
    w = w[["ACT_26", "BUD_26", "F5+7"]].reset_index()
    w["Var vs BUD"] = w["ACT_26"] - w["BUD_26"]
    w["Var %"] = w.apply(lambda r: safe_pct(r["ACT_26"] - r["BUD_26"], r["BUD_26"]), axis=1)
    w = w.reindex(w["ACT_26"].abs().sort_values(ascending=False).index)
    return w


# Cac thang co trong OPEX 2026 (de lam o chon ky)
_opex_2026 = sorted([p[-2:] for p in df["Period"].unique() if str(p).startswith("2026-")])
MONTH_NUM_NAME = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May",
                  "06": "Jun", "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct",
                  "11": "Nov", "12": "Dec"}

# Thu tu P&L chuan cho cac dong OPEX (dung chung nhieu tab)
OPEX_ORDER = [
    "Gross Std variance", "Other Cost of sales", "Direct costs", "Product Conception",
    "Storage", "Freight-Out", "Commercial", "Operational Marketing",
    "Advertising", "ASS", "General & Administrative", "Exchange differencies",
]
OPEX_DISPLAY = {
    "Gross Std variance": "Standard cost variances",
    "Other Cost of sales": "Other cost of sales",
    "Direct costs": "Direct costs",
    "Product Conception": "Research & Development",
    "Storage": "Storage expenses",
    "Freight-Out": "Freight out expenses",
    "Commercial": "Direct commercial expenses",
    "Operational Marketing": "Operational marketing expenses",
    "Advertising": "Advertising expenses",
    "ASS": "ASS expenses",
    "General & Administrative": "General & Administrative expenses",
    "Exchange differencies": "Exchange differences",
}


def opex_sort_key(pnl_line):
    """Tra ve thu tu de sap PnL Line theo cau truc P&L."""
    try:
        return OPEX_ORDER.index(pnl_line)
    except ValueError:
        return len(OPEX_ORDER)  # dong la xep cuoi


def period_selector(key):
    """O chon ky: YTD hoac 1 thang. Tra ve list ma thang (MM) hoac None = YTD."""
    opts = ["YTD"] + [MONTH_NUM_NAME.get(m, m) for m in _opex_2026]
    sel = st.radio("Kỳ:", opts, horizontal=True, key=key)
    if sel == "YTD":
        return None
    # doi ten thang -> so
    name_to_num = {v: k for k, v in MONTH_NUM_NAME.items()}
    return [name_to_num.get(sel, sel)]


def color_pn(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    if v > 0: return "color: #16a34a; font-weight: 700;"
    if v < 0: return "color: #dc2626; font-weight: 700;"
    return ""


def render_compare(w, dim_label):
    if w.empty:
        st.info("Khong co du lieu voi bo loc hien tai.")
        return

    col_tbl, col_chart = st.columns([1, 1.1])

    with col_tbl:
        show = w.copy()
        show.columns = [dim_label, "Actual 26", "Budget 26", "F5+7", "Var vs BUD", "Var %"]
        st.dataframe(
            show.style.format({"Actual 26": "{:,.0f}", "Budget 26": "{:,.0f}", "F5+7": "{:,.0f}",
                               "Var vs BUD": "{:,.0f}", "Var %": "{:+.1f}%"})
                .map(color_pn, subset=["Var vs BUD", "Var %"]),
            use_container_width=True, hide_index=True, height=480
        )

    with col_chart:
        wv = w.sort_values("Var vs BUD")
        bar_colors = [COLORS["POS"] if v >= 0 else COLORS["NEG"] for v in wv["Var vs BUD"]]
        fig = go.Figure(go.Bar(
            y=wv[wv.columns[0]], x=wv["Var vs BUD"], orientation="h",
            marker_color=bar_colors,
            text=[f"{v/1e9:+.1f}B" for v in wv["Var vs BUD"]],
            textposition="outside", cliponaxis=False,
        ))
        fig.add_vline(x=0, line_color="#94a3b8", line_width=1)
        fig.update_layout(height=480, template="seb_dark",
                          margin=dict(t=30, b=20, l=10, r=60),
                          xaxis_title="Var vs Budget (Actual − Budget)",
                          showlegend=False,
                          title=f"Variance vs Budget by {dim_label}")
        st.plotly_chart(fig, use_container_width=True)


with tab1:
    m1 = period_selector("pnl_period")
    src1 = dff[dff["Type"].isin(["ACT_26", "BUD_26", "F5+7"])]
    if m1:
        src1 = src1[src1["Period"].isin([f"2026-{x}" for x in m1])]

    if src1.empty:
        st.info("Khong co du lieu voi bo loc hien tai.")
    else:
        # Gom theo PnL Line + sub_PnL Line
        g = (src1.groupby(["PnL Line", "sub_PnL Line", "Type"], observed=True)["Amount"]
             .sum().reset_index())
        w = g.pivot_table(index=["PnL Line", "sub_PnL Line"], columns="Type",
                          values="Amount", aggfunc="sum").fillna(0)
        for c in ["ACT_26", "BUD_26", "F5+7"]:
            if c not in w.columns:
                w[c] = 0
        w = w[["ACT_26", "BUD_26", "F5+7"]].reset_index()
        w["Var vs BUD"] = w["ACT_26"] - w["BUD_26"]
        w["Var %"] = w.apply(lambda r: safe_pct(r["ACT_26"] - r["BUD_26"], r["BUD_26"]), axis=1)
        # Sap theo thu tu P&L cua PnL Line, roi theo Actual trong nhom
        w["_ord"] = w["PnL Line"].map(opex_sort_key)
        w = w.sort_values(["_ord", "ACT_26"], key=lambda s: s if s.name == "_ord" else s.abs())
        # Doi ten PnL Line hien thi cho dep
        w["PnL Line"] = w["PnL Line"].map(lambda x: OPEX_DISPLAY.get(x, x))

        col_tbl, col_chart = st.columns([1.25, 1])
        with col_tbl:
            show = w[["PnL Line", "sub_PnL Line", "ACT_26", "BUD_26", "Var vs BUD", "Var %"]].copy()
            show.columns = ["PnL Line", "sub_PnL Line", "Actual 26", "Budget 26", "Var vs BUD", "Var %"]
            st.dataframe(
                show.style.format({"Actual 26": "{:,.0f}", "Budget 26": "{:,.0f}",
                                   "Var vs BUD": "{:,.0f}", "Var %": "{:+.1f}%"})
                    .map(color_pn, subset=["Var vs BUD", "Var %"]),
                use_container_width=True, hide_index=True, height=520
            )
        with col_chart:
            # Chart theo PnL Line (gom sub lai), diverging Var
            byp = (w.groupby("PnL Line", observed=True)["Var vs BUD"].sum().reset_index()
                   .sort_values("Var vs BUD"))
            bar_colors = [COLORS["POS"] if v >= 0 else COLORS["NEG"] for v in byp["Var vs BUD"]]
            fig = go.Figure(go.Bar(
                y=byp["PnL Line"], x=byp["Var vs BUD"], orientation="h",
                marker_color=bar_colors,
                text=[f"{v/1e9:+.1f}B" for v in byp["Var vs BUD"]],
                textposition="outside", cliponaxis=False,
            ))
            fig.add_vline(x=0, line_color="#94a3b8", line_width=1)
            fig.update_layout(height=520, template="seb_dark",
                              margin=dict(t=30, b=20, l=10, r=60),
                              xaxis_title="Var vs Budget", showlegend=False,
                              title="Variance vs Budget by PnL Line")
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    m2 = period_selector("nature_period")
    src2 = dff[dff["Type"].isin(["ACT_26", "BUD_26", "F5+7"])]
    if m2:
        src2 = src2[src2["Period"].isin([f"2026-{x}" for x in m2])]
    w2 = compare_by("NATURE NAME", m2)
    if w2.empty:
        st.info("Khong co du lieu voi bo loc hien tai.")
    else:
        col_tbl, col_donut = st.columns([1, 1])
        with col_tbl:
            show = w2.copy()
            show.columns = ["NATURE NAME", "Actual 26", "Budget 26", "F5+7", "Var vs BUD", "Var %"]
            st.dataframe(
                show.style.format({"Actual 26": "{:,.0f}", "Budget 26": "{:,.0f}", "F5+7": "{:,.0f}",
                                   "Var vs BUD": "{:,.0f}", "Var %": "{:+.1f}%"})
                    .map(color_pn, subset=["Var vs BUD", "Var %"]),
                use_container_width=True, hide_index=True, height=480
            )
        with col_donut:
            # Donut chi phi Actual theo NATURE NAME (tri tuyet doi cho de doc)
            nat = w2.set_index("NATURE NAME")["ACT_26"]
            nat = nat[nat != 0].abs().sort_values(ascending=False)
            fig_d = go.Figure(go.Pie(
                labels=nat.index, values=nat.values, hole=0.5, textinfo="percent",
                marker=dict(colors=["#3b82f6", "#22d3ee", "#a78bfa", "#f59e0b",
                                    "#16a34a", "#9ca3af", "#ef4444", "#8b5cf6", "#14b8a6"])
            ))
            fig_d.update_layout(height=480, template="seb_dark",
                                margin=dict(t=30, b=10),
                                title="Actual Cost by NATURE NAME",
                                legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_d, use_container_width=True)

with tab5:
    st.subheader("Primary Contribution — YTD (KVND)")
    st.caption("Net Sales → SGM (tu Sales Dashboard) − chi phi OPEX = Primary Contribution.  "
               "OPEX tu dong khop ky voi thang cuoi cung cua Sales.")

    if not os.path.exists(SALES_FILE):
        st.error("Chua co data_cache.parquet (Sales). Chay convert_to_parquet.py truoc.")
    else:
        sales = pd.read_parquet(SALES_FILE)

        # Thang cuoi cung Sales co (theo MONTH_ORDER)
        sales_months = [m for m in MONTH_ORDER if m in sales["MONTH"].astype(str).unique()]
        if not sales_months:
            st.info("Sales khong co du lieu thang.")
        else:
            # ----- O chon: YTD hoac 1 thang cu the -----
            view_opts = ["YTD (tất cả)"] + sales_months
            sel_view = st.radio("Kỳ xem:", view_opts, horizontal=True, key="pc_period")

            if sel_view == "YTD (tất cả)":
                use_months = sales_months
                period_label = f"YTD (tới {sales_months[-1]})"
            else:
                use_months = [sel_view]
                period_label = sel_view

            last_num = MONTH_TO_NUM[use_months[-1]]

            # Loc Sales theo thang chon
            sfilt = sales[sales["MONTH"].astype(str).isin(use_months)]
            if sel_view == "YTD (tất cả)":
                st.info(f"Sales YTD tới **{sales_months[-1]}**. OPEX lấy các tháng tương ứng để khớp kỳ.")
            else:
                st.info(f"Xem riêng tháng **{sel_view}**. Cả Sales và OPEX chỉ lấy tháng này.")

            # ----- Phan tren: tu Sales (theo ky chon, KVND) -----
            def s_sum(prefix):
                return {
                    "GS": sfilt[f"GS_{prefix}"].sum(),
                    "NS": sfilt[f"NS_{prefix}"].sum(),
                    "DEDUCT": sfilt[f"DEDUCT_{prefix}"].sum(),
                    "COGS": sfilt[f"COGS_{prefix}"].sum(),
                    "SGM": sfilt[f"SGM_{prefix}"].sum(),
                }
            s_act = s_sum("ACT")
            s_bud = s_sum("BUD")

            # ----- OPEX khop ky, KVND -----
            opex_months = [f"2026-{MONTH_TO_NUM[m]}" for m in use_months]
            o_period = df[df["Period"].isin(opex_months)]

            def o_by_line(opex_type):
                g = (o_period[o_period["Type"] == opex_type]
                     .groupby("PnL Line", observed=True)["Amount"].sum() / 1000)
                return g

            o_act = o_by_line("ACT_26")
            o_bud = o_by_line("BUD_26")

            in_data = [x for x in o_act.index.tolist() + o_bud.index.tolist() if x]
            opex_lines = [x for x in OPEX_ORDER if x in in_data]
            opex_lines += [x for x in sorted(set(in_data)) if x not in OPEX_ORDER]

            # ----- Dung bang -----
            rows = []
            rows.append(("Gross Sales", s_act["GS"], s_bud["GS"], False))
            rows.append(("Sales Deductions", s_act["DEDUCT"], s_bud["DEDUCT"], False))
            rows.append(("Net Sales", s_act["NS"], s_bud["NS"], True))
            rows.append(("COGS (Standard)", s_act["COGS"], s_bud["COGS"], False))
            rows.append(("Standard Gross Margin", s_act["SGM"], s_bud["SGM"], True))
            for ln in opex_lines:
                disp = OPEX_DISPLAY.get(ln, ln)
                rows.append((disp, float(o_act.get(ln, 0)), float(o_bud.get(ln, 0)), False))

            # Primary Contribution = SGM + tong OPEX (OPEX am)
            pc_act = s_act["SGM"] + o_act.sum()
            pc_bud = s_bud["SGM"] + o_bud.sum()
            rows.append(("PRIMARY CONTRIBUTION", pc_act, pc_bud, True))

            tbl = pd.DataFrame(rows, columns=["Line", "Actual", "Budget", "_bold"])
            tbl["Var vs BUD"] = tbl["Actual"] - tbl["Budget"]
            tbl["% NS Act"] = tbl["Actual"] / s_act["NS"] * 100 if s_act["NS"] else 0

            # ----- KPI -----
            k1, k2, k3 = st.columns(3)
            k1.metric("Net Sales (KVND)", fmt_full(s_act["NS"]),
                      f"{safe_pct(s_act['NS']-s_bud['NS'], s_bud['NS']):+.1f}% vs BUD")
            k2.metric("Standard Gross Margin", fmt_full(s_act["SGM"]),
                      f"{safe_pct(s_act['SGM'], s_act['NS']):.1f}% of NS")
            k3.metric("Primary Contribution", fmt_full(pc_act),
                      f"{safe_pct(pc_act, s_act['NS']):.1f}% of NS")

            st.markdown("")

            # ----- Bang trai + chart waterfall phai -----
            col_tbl, col_wf = st.columns([1.2, 1])
            with col_tbl:
                bold_mask = tbl["_bold"].tolist()

                def style_row(row):
                    if bold_mask[row.name]:
                        return ["font-weight: 800; background-color: #dbeafe;"] * len(row)
                    return [""] * len(row)

                show = tbl[["Line", "Actual", "Budget", "Var vs BUD", "% NS Act"]].copy()
                st.dataframe(
                    show.style.apply(style_row, axis=1)
                    .format({"Actual": "{:,.0f}", "Budget": "{:,.0f}",
                             "Var vs BUD": "{:,.0f}", "% NS Act": "{:.1f}%"})
                    .map(color_pn, subset=["Var vs BUD"]),
                    use_container_width=True, hide_index=True, height=560
                )
            with col_wf:
                # Waterfall: NS -> +COGS(am) -> SGM -> +OPEX(am) -> Primary (Actual)
                wf_labels = ["Net Sales", "COGS", "SGM"] + \
                            [OPEX_DISPLAY.get(ln, ln)[:14] for ln in opex_lines] + ["Primary"]
                wf_meas = ["absolute", "relative", "total"] + \
                          ["relative"] * len(opex_lines) + ["total"]
                wf_vals = [s_act["NS"], s_act["COGS"], 0] + \
                          [float(o_act.get(ln, 0)) for ln in opex_lines] + [0]
                fig_wf = go.Figure(go.Waterfall(
                    orientation="v", measure=wf_meas, x=wf_labels, y=wf_vals,
                    connector=dict(line=dict(color="#94a3b8")),
                    increasing=dict(marker=dict(color="#16a34a")),
                    decreasing=dict(marker=dict(color="#dc2626")),
                    totals=dict(marker=dict(color="#3b82f6")),
                ))
                fig_wf.update_layout(height=560, template="seb_dark",
                                     margin=dict(t=30, b=80), xaxis_tickangle=-40,
                                     title="Waterfall — Net Sales → Primary (Actual)")
                st.plotly_chart(fig_wf, use_container_width=True)

with tab3:
    st.subheader(f"Detail ({len(dff):,} rows)")
    cols_show = [c for c in ["Type", "Period", "LE", "Cost Center Code",
                             "Cost Center Name", "PnL Line", "sub_PnL Line",
                             "NATURE NAME", "ME", "G/L Account Name", "Amount"]
                 if c in dff.columns]
    st.dataframe(
        dff[cols_show].style.format({"Amount": "{:,.0f}"}),
        use_container_width=True, hide_index=True, height=600
    )
