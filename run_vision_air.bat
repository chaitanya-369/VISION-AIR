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

:calibrate
echo.
echo [INFO] Starting Desk Calibration...
echo [GUIDE] Click 4 corners (TL -> TR -> BR -> BL), then press 's' to save.
python -m vision_air.core.calibration
if %errorlevel% neq 0 (
    echo [ERROR] Calibration failed or was cancelled.
    pause
) else (
    echo [SUCCESS] Calibration saved.
)
goto menu

:start_system
if not exist config.json (
    echo [WARNING] No calibration found! You must calibrate before starting.
    goto calibrate
)
echo.
echo [INFO] launching VISION-AIR Engine...
echo [INFO] Press 'q' in the camera window to quit safely.
python -m vision_air.main
if %errorlevel% neq 0 (
    echo [ERROR] System crashed or exited with an error.
    pause
)
goto menu

:install_deps
echo.
echo [INFO] Installing/Updating required libraries...
pip install -r requirements.txt
pip install -e .
echo [SUCCESS] Dependencies installed.
pause
goto menu
