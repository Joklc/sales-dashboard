# TÀI LIỆU BÀN GIAO — SEB Sales/Finance Dashboard

Tài liệu này dành cho bộ phận IT để hiểu và tích hợp (consolidate) dashboard này
vào hệ thống Streamlit sẵn có.

---

## 1. TỔNG QUAN

- **Nền tảng:** Streamlit (Python), multi-page dùng `st.navigation`.
- **Repo hiện tại:** GitHub `Joklc/sales-dashboard` (public), deploy trên Streamlit Cloud.
- **Ngôn ngữ dữ liệu:** Tiếng Việt + Anh. Đơn vị: Sales/Forecast = KVND, ROPA = KEUR, KAM = VND.
- **Cách chạy:** `python -m streamlit run Home.py`

## 2. CẤU TRÚC FILE

| File | Vai trò |
|------|---------|
| `Home.py` | Entry point. Khai báo `st.navigation`, gom 4 trang. |
| `page_sales.py` | Trang **Sales Dashboard** — Net Sales Actual/Budget/LY (YTD). |
| `page_pnl.py` | Trang **ROPA** — P&L (Sales→GM→ROPA), đơn vị KEUR. |
| `page_forecast.py` | Trang **Forecast vs Actual** — so Actual với các vòng forecast (F5+7...). |
| `page_kam_mtd.py` | Trang **Sales_MTD realtime** — MTD từ SQL, tự động hoá. |
| `page_mtd.py` | (Ẩn khỏi menu, giữ lại phòng dùng lại.) |

### Convert scripts (đọc Excel nguồn → xuất .parquet cache)
| Script | Input | Output |
|--------|-------|--------|
| `convert_to_parquet.py` | Excel Sales trên ổ X | `data_cache.parquet` |
| `convert_pnl.py` | Excel P&L trên ổ X | `pnl_cache.parquet` |
| `convert_forecast.py` | Excel forecast (pivot ngang) trên ổ X | `forecast_cache.parquet` |
| `convert_kam.py` | 3 file SQL + 5 file mapping | `kam_cache.parquet` |

**Pattern chung:** mỗi trang đọc từ file `*.parquet` (KHÔNG đọc Excel trực tiếp).
Convert tách riêng để trang load nhanh. Đây là điểm quan trọng khi tích hợp:
trang chỉ cần file parquet có mặt cùng thư mục.

## 3. LUỒNG DỮ LIỆU

```
[Nguồn Excel/SQL trên ổ mạng X:]
        │  (convert_*.py — chạy tay hoặc Task Scheduler)
        ▼
[*.parquet cache trong thư mục app]
        │  (Streamlit đọc, cache bằng @st.cache_data)
        ▼
[Dashboard hiển thị]
```

### Riêng trang KAM (Sales_MTD realtime) — tự động hoá:
- 3 file SQL subscription tự đẩy vào ổ X mỗi 15 phút:
  `Sales detail with COGS.xlsx` (ACT), `Sales Order Follow Up.xlsx` (SO),
  `Sales Quotation Status.xlsx` (SQ).
- `convert_kam.py` đọc 3 file này + 5 file mapping → gom nhóm, map, tính
  Net/COGS/SGM → xuất `kam_cache.parquet`.
- Windows Task Scheduler chạy `auto_update_kam.bat` mỗi 15 phút:
  convert → git push → Streamlit Cloud tự cập nhật.

## 4. LOGIC MAPPING KAM (quan trọng nhất)

`convert_kam.py` thay thế toàn bộ quy trình Power Query thủ công. Các bước:

1. Đọc 3 file nguồn (ACT/SO/SQ), mỗi file lấy: Customer, Item, Comm, Item name, Qty, Gross.
   - Tên cột Qty/Gross khác nhau giữa 3 file (xem dict `col` trong `build_source`).
2. Bỏ dòng Grand Total / rỗng (thiếu Customer hoặc Item).
3. Lọc: ACT giữ `CANCELED = N`; SO/SQ giữ Net > 0.
4. Gom nhóm theo **Customer + Item + Product Line**.
5. Map:
   - MLA + Channel ← `Customer map.xlsx` (theo Customer code)
   - Product Line ← `CMMF MAP.xlsx` (theo Item code)
   - PRSC KAM/FIN ← `PRSC_KAM-VAT.xlsx` / `PRSC_FIN-VAT.xlsx` (theo Item code)
   - Deduction rate KAM/FIN ← `Mapping deduction rate.xlsx` (dò MLA vào cột DEALER NAME)
6. VStack 3 nguồn → bỏ Channel = SEB và MLA = SEB (nội bộ).
7. Tính: `Net = Gross×(1−rate)`, `COGS = PRSC×Qty`, `SGM = Net − COGS`.

**Lưu ý dữ liệu:**
- Customer code / Item code cần chuẩn hoá (bỏ hậu tố `.0`) trước khi map — xem `clean_code()`.
- File `Mapping deduction rate.xlsx` đọc từ folder RIÊNG (`X:\Finance 2.Controlling\Dashboard`),
  không phải folder auto data — để user tự sửa rate không bị SQL ghi đè.
- Nếu Item chưa có trong CMMF MAP → Product Line = NaN → dòng đó bị loại khỏi groupby,
  gây lệch tổng. Chạy `export_missing.py` để lấy danh sách Item cần bổ sung.

## 5. RECONCILE TÊN GIỮA CÁC NGUỒN (đã xử lý sẵn trong code)

- **Family Level 2** khác nhau giữa Actual (viết tắt) và Forecast (đầy đủ):
  xử lý bằng `FAMILY_MAP` trong `page_forecast.py`.
- **Product Line** khác nhau giữa KAM (`&`) và Forecast (`AND`):
  xử lý bằng `PL_MAP` trong `page_kam_mtd.py`.
- **Đơn vị:** forecast là KVND, KAM là VND → forecast ×1000 khi so sánh.

## 6. TÍCH HỢP VÀO DASHBOARD STREAMLIT SẴN CÓ

Vì cả hai đều là Streamlit multi-page, cách gộp đơn giản nhất:

**Cách A — Thêm các trang này vào `st.navigation` của dashboard IT:**
1. Copy 4 file `page_*.py` + các file `convert_*.py` + các `*.parquet` vào project IT.
2. Trong `Home.py` (hoặc entry point của IT), thêm:
   ```python
   sales_page = st.Page("page_sales.py", title="Sales Dashboard", icon=":material/bar_chart:")
   pnl_page   = st.Page("page_pnl.py",   title="ROPA",   icon=":material/payments:")
   fc_page    = st.Page("page_forecast.py", title="Forecast vs Actual", icon=":material/insights:")
   kam_page   = st.Page("page_kam_mtd.py", title="Sales_MTD realtime", icon=":material/groups:")
   ```
   rồi thêm các page đó vào list `st.navigation([...])` sẵn có.
3. Đảm bảo các file `.parquet` nằm cùng thư mục với các `page_*.py`
   (các page dùng `os.path.dirname(os.path.abspath(__file__))` để tìm parquet).

**Cách B — Gom vào section riêng:** dùng `st.navigation` dạng dict để nhóm
các trang này thành 1 section (vd "Finance") tách khỏi trang của IT.

**Lưu ý khi tích hợp:**
- Mỗi `page_*.py` có block CSS riêng ở đầu (theme). Nếu muốn đồng bộ theme với
  dashboard IT, chỉnh phần `st.markdown(...<style>...)` ở đầu mỗi file.
- Tên dòng P&L, tên cột trong file nguồn phải khớp — xem mục 4, 5.
- Nút "Refresh data" trong `page_kam_mtd.py` chỉ hiện khi chạy local (detect ổ X).
  Trên cloud/server không có ổ X thì nút tự ẩn.

## 7. THƯ VIỆN CẦN CÀI

```
streamlit pandas plotly pyarrow openpyxl xlsxwriter pyodbc
```

## 8. FILE PHỤ TRỢ

- `auto_update_kam.bat` — convert + git push (gọi bởi Task Scheduler mỗi 15').
- `start_dashboard.bat` — mở dashboard local bằng nhấp đúp.
- `export_missing.py` — xuất danh sách Item chưa map CMMF.
- `secrets.toml` (local) — mật khẩu app. KHÔNG commit file này lên git.

---

**Người bàn giao:** Jo (Finance, Groupe SEB Vietnam)
**Ghi chú:** Toàn bộ logic mapping đã verify khớp công thức với file Excel gốc (Power Query cũ).
