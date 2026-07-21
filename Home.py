import streamlit as st

st.set_page_config(page_title="SEB Dashboard", layout="wide", initial_sidebar_state="expanded")

# ==================================================
# PASSWORD GATE — màn hình đăng nhập
# ==================================================

def check_password():
    """Hiện ô nhập mật khẩu. Trả về True nếu đúng."""

    def password_entered():
        # Lấy mật khẩu từ secrets (an toàn), fallback nếu chưa cấu hình
        correct = st.secrets.get("app_password", "SEB2026")
        if st.session_state.get("pwd_input", "") == correct:
            st.session_state["authenticated"] = True
            del st.session_state["pwd_input"]  # xóa mật khẩu khỏi bộ nhớ
        else:
            st.session_state["authenticated"] = False

    if st.session_state.get("authenticated", False):
        return True

    # Màn hình đăng nhập
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔒 Groupe SEB — Sales & P&L Dashboard")
        st.text_input("Please enter password to access:", type="password",
                      key="pwd_input", on_change=password_entered)
        if "authenticated" in st.session_state and not st.session_state["authenticated"]:
            st.error("❌ Incorrect password. Please try again.")
        st.caption("Please contact the Finance team if you don't have the password.")
    return False

if not check_password():
    st.stop()

# ==================================================
# NAVIGATION — sau khi đăng nhập thành công
# ==================================================

sales_page = st.Page("page_sales.py", title="Sales Dashboard", icon=":material/bar_chart:", default=True)
pnl_page   = st.Page("page_pnl.py",   title="ROPA",   icon=":material/payments:")
fc_page    = st.Page("page_forecast.py", title="Forecast vs Actual", icon=":material/insights:")
mtd_page   = st.Page("page_mtd.py",   title="Realtime MTD Sale", icon=":material/bolt:")
kam_page   = st.Page("page_kam_mtd.py", title="KAM_MTD realtime", icon=":material/groups:")

pg = st.navigation([sales_page, pnl_page, fc_page, mtd_page, kam_page])
pg.run()
