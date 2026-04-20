@echo off
setlocal enabledelayedexpansion
set PYTHONPATH=src;%PYTHONPATH%

title VISION-AIR - Virtual Spatial Interface

:: Aesthetic Header
echo.
echo  ###############################################################
echo  #                                                             #
echo  #          VISION-AIR: VIRTUAL SPATIAL INTERFACE              #
echo  #          -------------------------------------              #
echo  #          "The desk is your interface"                       #
echo  #                                                             #
echo  ###############################################################
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b
)

:: Menu System
:menu
echo [1] START VISION-AIR (Main System)
echo [2] CALIBRATE DESK (Run this first time or if camera moved)
echo [3] INSTALL / UPDATE DEPENDENCIES
echo [4] EXIT
echo.
set /p choice="Select an option [1-4]: "

if "%choice%"=="1" goto start_system
if "%choice%"=="2" goto calibrate
if "%choice%"=="3" goto install_deps
if "%choice%"=="4" exit /b
goto menu

:install_deps
echo.
echo [INFO] Creating Virtual Environment (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create venv. Make sure Python 3.12 is installed and in PATH.
    pause
    goto menu
)

echo [INFO] Activating Environment and Installing dependencies...
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
echo [SUCCESS] Dependencies installed in .venv.
pause
goto menu

:start_system
if not exist .venv (
    echo [WARNING] Virtual Environment not found! Running Installation first...
    goto install_deps
)
if not exist config.json (
    echo [WARNING] No calibration found! You must calibrate before starting.
    goto calibrate
)
echo.
echo [INFO] Activating Environment...
call .venv\Scripts\activate
echo [INFO] Launching VISION-AIR Engine...
python -m vision_air.main
if %errorlevel% neq 0 (
    echo [ERROR] System crashed.
    pause
)
goto menu

:calibrate
if not exist .venv (
    echo [WARNING] Virtual Environment not found! Running Installation first...
    goto install_deps
)
echo.
echo [INFO] Activating Environment...
call .venv\Scripts\activate
echo [INFO] Starting Desk Calibration...
python -m vision_air.core.calibration
goto menu
