@echo off
setlocal EnableDelayedExpansion

set "UV_CMD=uv"
set "ROOT=%~dp0"
set "VENV_DIR=%ROOT%venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "PYTHON_CMD=python"

if defined VIRTUAL_ENV (
    echo Detected active virtual environment "%VIRTUAL_ENV%".
    echo Please deactivate it before running run.bat so the correct Python version can be used.
    goto fail_setup
)

where %UV_CMD% >nul 2>&1
if errorlevel 1 (
    echo uv is required but was not found on PATH.
    echo Install it from https://docs.astral.sh/uv/getting-started/installation/ and rerun this script.
    goto fail_setup
)

call :select_python_interpreter
if errorlevel 1 goto fail_setup

echo Starting Visual Search AI Service...

if exist "%VENV_PYTHON%" (
    set "VENV_VERSION="
    for /f "tokens=2 delims= " %%V in ('"%VENV_PYTHON%" -V 2^>^&1') do set "VENV_VERSION=%%V"
    "%VENV_PYTHON%" -c "import sys; sys.exit(0 if (sys.version_info.major==3 and 8<=sys.version_info.minor<=11) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Existing virtualenv uses Python !VENV_VERSION!; recreating with %PYTHON_CMD%...
        rmdir /s /q "%VENV_DIR%"
    )
)

if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment with %PYTHON_CMD%...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto fail_setup
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Virtual environment missing activation scripts; recreating...
    rmdir /s /q "%VENV_DIR%"
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto fail_setup
)

if not exist "%VENV_PYTHON%" (
    echo Virtual environment Python executable missing at "%VENV_PYTHON%".
    goto fail_setup
)

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo Installing Python dependencies...
%UV_CMD% pip install --python "%VENV_PYTHON%" -r requirements.txt
if errorlevel 1 goto fail_setup
echo(

echo Installing PyTorch (CUDA-aware)...
"%VENV_PYTHON%" scripts\install_pytorch.py
if errorlevel 1 goto fail_setup
echo(

if not exist "data\catalog" (
    mkdir data\catalog
)

if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    pushd frontend
    call npm install || goto fail_setup
    popd
    echo(
)

echo Starting backend server...
start "Backend" cmd /k "cd /d %ROOT% && call venv\Scripts\activate.bat && python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

echo Starting frontend server...
pushd frontend
start "Frontend" cmd /k "npm start"
popd

echo(
echo Services started!
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo(
echo Close the command windows to stop services

pause
goto :eof

:select_python_interpreter
REM Prefer Python 3.11 from the py launcher
py -3.11 -V >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3.11"
    echo Using Python 3.11 via "py -3.11".
    exit /b 0
)

for /f "tokens=2 delims= " %%V in ('python -V 2^>^&1') do set "HOST_PY_VERSION=%%V"
if defined HOST_PY_VERSION (
    for /f "tokens=1,2 delims=." %%A in ("%HOST_PY_VERSION%") do (
        set "HOST_PY_MAJOR=%%A"
        set "HOST_PY_MINOR=%%B"
    )
    if "!HOST_PY_MAJOR!"=="3" (
        if !HOST_PY_MINOR! GEQ 8 if !HOST_PY_MINOR! LEQ 11 (
            set "PYTHON_CMD=python"
            echo Using system Python !HOST_PY_VERSION!.
            exit /b 0
        )
    )
)

echo Python 3.8-3.11 is required (PyTorch wheels are not published for newer versions).
echo Install Python 3.11 and ensure "py -3.11" works, then rerun this script.
exit /b 1

:fail_setup
echo(
echo Setup aborted. Please resolve the issues above and rerun this script.
exit /b 1

