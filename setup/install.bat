@echo off
chcp 65001 >nul
echo ===================================================
echo   Hia Wiki Memory - Khoi chay trinh cai dat
echo ===================================================

cd %~dp0\..

python --version >nul 2>&1
if errorlevel 1 (
    echo [Loi] Python chua duoc cai dat hoac chua them vao PATH.
    echo Vui long cai dat Python 3.10+ de tiep tuc.
    pause
    exit /b 1
)

echo Dang khoi dong setup_env.py...
python setup\setup_env.py

pause
