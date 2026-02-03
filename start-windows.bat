@echo off
echo ========================================
echo Bain Productivity Tool - Windows Startup
echo ========================================

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Check for Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

:: Create demo-docs folder if it doesn't exist
if not exist demo-docs (
    echo Creating demo-docs folder...
    mkdir demo-docs
)

:: Copy .env if it doesn't exist
if not exist backend\.env (
    if exist .env.example (
        echo Copying .env.example to backend\.env...
        copy .env.example backend\.env
    )
)

:: Start backend
echo.
echo Starting backend...
cd backend
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt --quiet
start "Backend Server" cmd /k "venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
cd ..

:: Wait for backend
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Start frontend
echo.
echo Starting frontend...
cd frontend
if not exist node_modules (
    echo Installing npm dependencies...
    call npm install
)
start "Frontend Dev Server" cmd /k "npm run dev"
cd ..

:: Wait and open browser
echo.
echo Waiting for frontend to start...
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo ========================================
echo Servers are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo ========================================
pause
