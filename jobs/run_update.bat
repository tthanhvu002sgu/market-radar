@echo off
rem ===================================================================
rem Market Radar - Tu dong cap nhat du lieu thi truong S&P 500
rem Script nay duoc thiet ke de chay tu dong bang Windows Task Scheduler
rem hoac co the click dup chuot de chay thu cong trong nen.
rem ===================================================================

rem Chuyen ve thu muc goc cua Market Radar
cd /d "%~dp0\.."

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
    echo [ERROR] Khong tim thay Python trong he thong.
    exit /b 1
)

rem Tao thu muc ghi log neu chua ton tai
if not exist "logs" mkdir "logs"

echo ===================================================== >> "logs\scheduler.log"
echo [START] %date% %time% - Bat dau tien trinh cap nhat du lieu >> "logs\scheduler.log"

rem Chay pipeline cap nhat va chuyen toan bo output vao file log
"%PYTHON_CMD%" -m jobs.update_pipeline >> "logs\scheduler.log" 2>&1

if %ERRORLEVEL% equ 0 (
    echo [FINISH] %date% %time% - Cap nhat snapshot thanh cong! >> "logs\scheduler.log"
) else (
    echo [ERROR] %date% %time% - Tien trinh ket thuc voi ma loi %ERRORLEVEL% >> "logs\scheduler.log"
)
echo ===================================================== >> "logs\scheduler.log"
