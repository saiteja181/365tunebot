@echo off
REM ============================================================================
REM 365 Tune Bot - Start Server with Tenant Security
REM ============================================================================

echo.
echo ============================================================================
echo  365 TUNE BOT - Starting with Tenant Security
echo ============================================================================
echo.
echo Your Tenant Code: 6c657194-e896-4367-a285-478e3ef159b6
echo.
echo Security Features Active:
echo  [x] Automatic tenant filtering on all queries
echo  [x] SQL injection prevention
echo  [x] Dangerous operations blocked (DROP, DELETE, etc.)
echo  [x] Audit logging enabled
echo.
echo ============================================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if exist venv (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Using system Python...
)

REM Install/check dependencies
echo Checking dependencies...
pip install -q fastapi uvicorn pyodbc pandas sqlparse 2>nul

echo.
echo Starting FastAPI server...
echo.
echo ============================================================================
echo  Server will be available at:
echo  - Main: http://localhost:8000
echo  - API Docs: http://localhost:8000/docs
echo  - Health Check: http://localhost:8000/health
echo ============================================================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python real_fastapi.py

pause
