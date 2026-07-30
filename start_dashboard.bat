@echo off
REM ============================================================
REM  Mo SEB Dashboard (local)
REM  Nhap dup file nay de mo dashboard, khong can go lenh.
REM ============================================================

title SEB Dashboard - DANG CHAY (dung dong cua so nay khi con xem dashboard)

cd /d C:\AI_Dashboard

echo ============================================================
echo   Dang khoi dong SEB Dashboard (local)...
echo   Trinh duyet se tu mo sau vai giay.
echo.
echo   LUU Y:
echo   - GIU cua so den nay mo trong luc xem dashboard.
echo   - Trang KAM: bam nut "Refresh data" de cap nhat so moi,
echo     sau do nho git push de dong nghiep xem duoc tren cloud.
echo   - Dong cua so nay (hoac bam Ctrl+C) khi muon tat dashboard.
echo ============================================================
echo.

python -m streamlit run Home.py

REM Neu streamlit thoat (loi hoac tat), giu cua so lai de doc thong bao
echo.
echo ============================================================
echo   Dashboard da dung.
echo ============================================================
pause
