@echo off
REM ============================================================
REM  Tu dong: chay convert_kam.py -> push len GitHub
REM  Duoc goi moi 15 phut boi Windows Task Scheduler.
REM  Ghi log vao auto_push.log de kiem tra khi can.
REM ============================================================

cd /d C:\AI_Dashboard

echo ============================================================ >> auto_push.log
echo [%date% %time%] Bat dau >> auto_push.log

REM 1. Chay convert (doc file SQL moi tu o X, tao kam_cache.parquet)
python convert_kam.py >> auto_push.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] LOI convert_kam.py - bo qua lan nay >> auto_push.log
    goto :end
)

REM 2. Kiem tra co thay doi khong; neu khong thi bo qua (khoi push rong)
git diff --quiet kam_cache.parquet
if not errorlevel 1 (
    echo [%date% %time%] Khong co thay doi data - khong push >> auto_push.log
    goto :end
)

REM 3. Push len GitHub
git add kam_cache.parquet >> auto_push.log 2>&1
git commit -m "Auto update KAM %date% %time%" >> auto_push.log 2>&1
git push >> auto_push.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] LOI khi push - thu pull roi push lai >> auto_push.log
    git pull origin main --no-edit >> auto_push.log 2>&1
    git push >> auto_push.log 2>&1
)

echo [%date% %time%] Xong >> auto_push.log

:end
