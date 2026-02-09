@echo off
chcp 65001 >nul 2>&1
REM SQLite database setup and apply Alembic migrations (Windows)
REM Location: scripts\databaseSetup\setup_sqlite.bat
REM Usage:
REM   setup_sqlite.bat [DB_FILE]
REM   - If DB_FILE is provided it will be used (absolute or relative path).
REM   - Otherwise use environment variable SQLITE_DB_FILE or default: .\data\sqlite.db

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\..") do set REPO_ROOT=%%~fI\

REM Positional argument (optional) - will override values loaded from .env
set ARG1=%~1

REM Load .env file from the repo root if present. Values are only set if not already defined
if exist "%REPO_ROOT%.env" (
  echo [INFO] Loading env from %REPO_ROOT%.env
  for /f "usebackq tokens=1* delims==" %%A in ("%REPO_ROOT%.env") do (
    if not "%%A"=="" (
      if /I "%%~A"=="SQLITE_DB_FILE" if not defined SQLITE_DB_FILE set "SQLITE_DB_FILE=%%~B"
      if /I "%%~A"=="DATABASE_URL" if not defined DATABASE_URL set "DATABASE_URL=%%~B"
      if /I "%%~A"=="SQLITE_JOURNAL_MODE" if not defined SQLITE_JOURNAL_MODE set "SQLITE_JOURNAL_MODE=%%~B"
      if /I "%%~A"=="SQLITE_SYNCHRONOUS" if not defined SQLITE_SYNCHRONOUS set "SQLITE_SYNCHRONOUS=%%~B"
      if /I "%%~A"=="SQLITE_TIMEOUT" if not defined SQLITE_TIMEOUT set "SQLITE_TIMEOUT=%%~B"
      if /I "%%~A"=="SQLITE_FOREIGN_KEYS" if not defined SQLITE_FOREIGN_KEYS set "SQLITE_FOREIGN_KEYS=%%~B"
    )
  )
)

REM Positional argument overrides .env and defaults
if not "%ARG1%"=="" (
  set DB_FILE=%ARG1%
) else if defined SQLITE_DB_FILE (
  set DB_FILE=%SQLITE_DB_FILE%
) else (
  set DB_FILE=%REPO_ROOT%data\sqlite.db
)

REM Ensure directory exists
for %%P in ("%DB_FILE%") do set DB_DIR=%%~dpP
if not exist "%DB_DIR%" mkdir "%DB_DIR%"

REM Create file if missing using python
if not exist "%DB_FILE%" (
  if exist "%SystemRoot%\System32\sqlite3.exe" (
    sqlite3 "%DB_FILE%" "VACUUM;" >nul 2>&1 || rem ignore
  ) else (
    %SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "[void](New-Item -ItemType File -Path '%DB_FILE%' -Force)" 2>nul || (
      python -c "import sqlite3, os; os.makedirs(os.path.dirname(r'%DB_FILE%'), exist_ok=True); sqlite3.connect(r'%DB_FILE%').close()"
    )
  )
)

REM Detect Python in venv
if exist ".venv\Scripts\python.exe" (
  set PYTHON_CMD=.venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
  set PYTHON_CMD=venv\Scripts\python.exe
) else (
  set PYTHON_CMD=python
)

echo Using SQLite DB file: %DB_FILE%

if not defined DATABASE_URL (
  REM Convert to file URI for SQLAlchemy. Use forward slashes and absolute path.
  for %%F in ("%DB_FILE%") do set ABS=%%~fF
  set ABS=%ABS:\=/%
  set DATABASE_URL=sqlite:///%ABS%
  setx DATABASE_URL "%DATABASE_URL%" >nul
  echo Exported DATABASE_URL=%DATABASE_URL%
)

%PYTHON_CMD% -m alembic --version >nul 2>&1 || (
  echo [ERROR] Alembic not found. Install: %PYTHON_CMD% -m pip install alembic
  exit /b 1
)

echo Running Alembic migrations (upgrade head)...
%PYTHON_CMD% -m alembic upgrade head
if %errorlevel% neq 0 (
  echo [ERROR] Alembic migration failed
  exit /b 1
)

endlocal
echo [SUCCESS] SQLite DB ready: %DB_FILE%
exit /b 0
