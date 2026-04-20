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

:: Menu System
:menu
echo [1] START VISION-AIR (Main System)
echo [2] CALIBRATE DESK (Run this first time)
echo [3] INSTALL / UPDATE DEPENDENCIES (Safe Clean)
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
echo [INFO] Performing Deep Clean of .venv...
if exist .venv (
    rmdir /s /q .venv
)

:: Find the best Python version
set PY_CMD=python
py -3.12 --version >nul 2>&1 && set PY_CMD=py -3.12
py -3.11 --version >nul 2>&1 && set PY_CMD=py -3.11

echo [INFO] Creating Fresh Virtual Environment using: %PY_CMD%
%PY_CMD% -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create venv. 
    echo Please make sure Python 3.11 or 3.12 is installed.
    pause
    goto menu
)

echo [INFO] Activating Environment and Installing dependencies...
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
echo.
echo [SUCCESS] MISSION COMPLETE: Environment is now ready.
echo [CHECK] Final Python Version in Venv:
python --version
pause
goto menu

:start_system
if not exist .venv (
    echo [WARNING] Virtual Environment not found! Running Installation first...
    pause
    goto install_deps
)
echo.
echo [INFO] Activating Environment...
call .venv\Scripts\activate
echo [INFO] System Check...
python --version | findstr "3.13" >nul 2>&1
if errorlevel 1 (
    echo [OK] Version Check Passed.
) else (
    echo [CAUTION] WARNING: You are still using Python 3.13! 
    echo MediaPipe will NOT work. Please run Option 3 again.
    pause
    goto menu
)

echo [INFO] Launching VISION-AIR Engine...
python -m vision_air.main
if errorlevel 1 (
    echo [ERROR] System crashed or was closed.
    pause
)
goto menu

:calibrate
if not exist .venv (
    echo [WARNING] Virtual Environment not found! Running Installation first...
    pause
    goto install_deps
)
echo.
echo [INFO] Activating Environment...
call .venv\Scripts\activate
echo [INFO] Starting Desk Calibration...
python -m vision_air.core.calibration
goto menu
