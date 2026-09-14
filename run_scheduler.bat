@echo off
title Market Radar - Automated Scheduler
rem ===================================================================
rem Khoi chay tien trinh Scheduler tu dong theo khung gio chuan
rem 05:00, 11:00, 17:00, 23:00 (Moi 6 tieng)
rem ===================================================================

cd /d "%~dp0"

echo Dang kiem tra moi truong Python...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Khong tim thay Python trong PATH.
    pause
    exit /b 1
)

echo.
echo ===================================================================
echo   KHOI DONG MARKET RADAR SCHEDULER THEO KHUNG GIO CHUAN
echo   Cac moc gio: 05:00 - 11:00 - 17:00 - 23:00 (Moi 6 tieng)
echo   Nhan Ctrl + C de dung tien trinh bat ky luc nao
echo ===================================================================
echo.

python -m jobs.scheduler %*

pause
