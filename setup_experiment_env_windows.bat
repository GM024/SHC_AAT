@echo off
setlocal

set "ROOT_DIR=%~dp0"
for %%I in ("%ROOT_DIR%..") do set "PROJECT_PARENT=%%~fI"
set "DEFAULT_VENV=%PROJECT_PARENT%\.venv-experiment310"

if not "%~1"=="" (
  set "VENV_PATH=%~f1"
) else (
  set "VENV_PATH=%DEFAULT_VENV%"
)

if defined PYTHON_BIN (
  set "PYTHON_CMD=%PYTHON_BIN%"
) else (
  set "PYTHON_CMD=py -3.10"
)

echo Creating experiment environment at:
echo   %VENV_PATH%
echo.

call %PYTHON_CMD% -m venv "%VENV_PATH%"
if errorlevel 1 (
  echo Failed to create the virtual environment.
  echo Make sure Python 3.10 is installed, or set PYTHON_BIN to a working python.exe.
  exit /b 1
)

"%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

"%VENV_PATH%\Scripts\pip.exe" install -r "%ROOT_DIR%requirements-experiment.txt"
if errorlevel 1 exit /b 1

"%VENV_PATH%\Scripts\python.exe" "%ROOT_DIR%Verification scripts\check_experiment_env.py"
if errorlevel 1 exit /b 1

echo.
echo Experiment environment ready.
echo Venv: %VENV_PATH%
echo.
echo Optional environment overrides:
echo   set MRP_PYTHON=%VENV_PATH%\Scripts\python.exe
echo   set MRP_LOGBOOK_PATH=C:\path\to\MRP_Logbook.xlsx
echo.
echo Run launchers from:
echo   %ROOT_DIR%Windows scripts
exit /b 0
