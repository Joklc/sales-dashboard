@echo off
REM ============================================================
REM  Tu dong: chay convert_kam.py + convert_mtd.py -> push GitHub
REM  Duoc goi moi 15 phut boi Windows Task Scheduler.
REM  Push CA 2 file: kam_cache.parquet va mtd_cache.parquet
REM  Ghi log vao auto_push.log de kiem tra khi can.
REM ============================================================

cd /d C:\AI_Dashboard

echo ============================================================ >> auto_push.log
echo [%date% %time%] Bat dau >> auto_push.log

REM 1a. Chay convert KAM (tao kam_cache.parquet)
python convert_kam.py >> auto_push.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] LOI convert_kam.py - bo qua lan nay >> auto_push.log
    goto :end
)

REM 1b. Chay convert MTD (tao mtd_cache.parquet - dung cho tab Family Level 2)
python convert_mtd.py >> auto_push.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] LOI convert_mtd.py - van tiep tuc push kam >> auto_push.log
)

REM 2. Kiem tra co thay doi khong o CA 2 file; neu khong doi thi bo qua
git diff --quiet kam_cache.parquet mtd_cache.parquet
if not errorlevel 1 (
    echo [%date% %time%] Khong co thay doi data - khong push >> auto_push.log
    goto :end
)

REM 3. Push len GitHub (ca 2 file)
git add kam_cache.parquet mtd_cache.parquet >> auto_push.log 2>&1
git commit -m "Auto update KAM + MTD %date% %time%" >> auto_push.log 2>&1
git push >> auto_push.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] LOI khi push - thu pull roi push lai >> auto_push.log
    git pull origin main --no-edit >> auto_push.log 2>&1
    git push >> auto_push.log 2>&1
)

echo [%date% %time%] Xong >> auto_push.log

:end
