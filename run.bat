@echo off
echo Starting Visual Search AI Service...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Create data directory
if not exist "data\catalog" mkdir data\catalog

REM Start backend
echo Starting backend server...
start "Backend" cmd /k "uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a bit for backend to start
timeout /t 5 /nobreak

REM Install and start frontend
echo Setting up frontend...
cd frontend

if not exist "node_modules" (
    echo Installing Node dependencies...
    call npm install
)

echo Starting frontend server...
start "Frontend" cmd /k "npm start"

echo.
echo Services started!
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo.
echo Close the command windows to stop services

pause