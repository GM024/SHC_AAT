@echo off
setlocal

if "%~1"=="" (
  echo Missing task script path.
  exit /b 1
)

set "SCRIPT_REL=%~1"
set "TASK_LABEL=%~2"
set "ROOT_DIR=%~dp0"
for %%I in ("%ROOT_DIR%..") do set "PROJECT_ROOT=%%~fI"
for %%I in ("%PROJECT_ROOT%..") do set "PROJECT_PARENT=%%~fI"
set "CACHE_DIR=%PROJECT_ROOT%\cache"
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"
set "PYTHONPYCACHEPREFIX=%CACHE_DIR%"

if defined MRP_PYTHON (
  set "VENV_PYTHON=%MRP_PYTHON%"
) else (
  set "VENV_PYTHON=%PROJECT_PARENT%\.venv-experiment310\Scripts\python.exe"
  if not exist "%VENV_PYTHON%" (
    set "VENV_PYTHON=%PROJECT_ROOT%\.venv-experiment310\Scripts\python.exe"
  )
)

set "SCRIPT_PATH=%PROJECT_ROOT%\%SCRIPT_REL%"

if not exist "%SCRIPT_PATH%" (
  echo Could not find task script:
  echo   %SCRIPT_PATH%
  pause
  exit /b 1
)

if not exist "%VENV_PYTHON%" (
  echo Could not find the experiment Python interpreter.
  echo.
  echo Checked:
  echo   %VENV_PYTHON%
  echo.
  echo Fix one of these first:
  echo   1. Create the dedicated project environment on Windows
  echo   2. Or set MRP_PYTHON to the PsychoPy/experiment python.exe path
  pause
  exit /b 1
)

title %TASK_LABEL%
echo Launching %TASK_LABEL%...
echo Python: %VENV_PYTHON%
echo Script: %SCRIPT_PATH%
echo.

"%VENV_PYTHON%" "%SCRIPT_PATH%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo %TASK_LABEL% exited with code %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
