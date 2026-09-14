@echo off
title Market Radar - Automated Scheduler
rem ===================================================================
rem Khoi chay tien trinh Scheduler tu dong theo khung gio chuan
rem 05:00, 11:00, 17:00, 23:00 (Moi 6 tieng)
rem ===================================================================

cd /d "%~dp0"

set "PYTHON_CMD="
if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_CMD=python"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Khong tim thay Python trong PATH hoac thu muc venv.
    echo Vui long cai dat Python hoac tao virtualenv truoc khi chay.
    pause
    exit /b 1
)

rem Kiem tra pandas trong moi truong Python duoc chon
"%PYTHON_CMD%" -c "import pandas" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo ===================================================================
    echo [ERROR] Moi truong Python "%PYTHON_CMD%" CHUA CO PANDAS!
    echo ===================================================================
    echo Ban can cai dat cac thu vien can thiet bang lenh:
    echo     pip install -r requirements.txt
    echo Hoac neu dang dung venv:
    echo     .\venv\Scripts\pip install -r requirements.txt
    echo ===================================================================
    echo.
    pause
    exit /b 1
)

echo.
echo ===================================================================
echo   KHOI DONG MARKET RADAR SCHEDULER THEO KHUNG GIO CHUAN
echo   Python: %PYTHON_CMD%
echo   Cac moc gio: 05:00 - 11:00 - 17:00 - 23:00 (Moi 6 tieng)
echo   Nhan Ctrl + C de dung tien trinh bat ky luc nao
echo ===================================================================
echo.

"%PYTHON_CMD%" -m jobs.scheduler %*

pause
