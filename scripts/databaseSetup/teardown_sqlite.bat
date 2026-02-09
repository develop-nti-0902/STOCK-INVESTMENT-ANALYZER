@echo off
chcp 65001 >nul 2>&1
REM SQLite database teardown and remove DB file (Windows)
REM Location: scripts\databaseSetup\teardown_sqlite.bat
REM Usage:
REM   teardown_sqlite.bat [DB_FILE]
REM   - If DB_FILE is provided it will be used (absolute or relative path).
REM   - Otherwise use environment variable SQLITE_DB_FILE or DATABASE_URL or default: .\data\sqlite.db

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
    )
  )
)

REM Positional argument overrides .env and defaults
if not "%ARG1%"=="" (
  set DB_FILE=%ARG1%
) else if defined SQLITE_DB_FILE (
  set DB_FILE=%SQLITE_DB_FILE%
) else if defined DATABASE_URL (
  set DB_FILE=%DATABASE_URL%
) else (
  set DB_FILE=%REPO_ROOT%data\sqlite.db
)

REM If DB_FILE is a sqlite URL (sqlite:///C:/path) strip prefix
if "%DB_FILE:~0,10%"=="sqlite:///" (
  set DB_FILE=%DB_FILE:~10%
)

REM Convert forward slashes to backslashes for Windows paths
set DB_FILE=%DB_FILE:/=\%

echo Using SQLite DB file: %DB_FILE%

REM Detect Python in venv
if exist ".venv\Scripts\python.exe" (
  set PYTHON_CMD=.venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
  set PYTHON_CMD=venv\Scripts\python.exe
) else (
  set PYTHON_CMD=python
)

if not exist "%DB_FILE%" (
  echo [INFO] DB file does not exist: %DB_FILE% — nothing to teardown
  endlocal
  exit /b 0
)

%PYTHON_CMD% -m alembic --version >nul 2>&1 || (
  echo [ERROR] Alembic not found. Install: %PYTHON_CMD% -m pip install alembic
  exit /b 1
)

echo Running Alembic downgrade to base (if alembic history present)...
REM Ensure DATABASE_URL points to the target DB for Alembic run
if not defined DATABASE_URL (
  for %%F in ("%DB_FILE%") do set ABS=%%~fF
  set ABS=%ABS:\=/%
  set DATABASE_URL=sqlite:///%ABS%
)

REM Use local environment variable for this process only
setlocal DISABLEDELAYEDEXPANSION
set "OLD_DBURL=%DATABASE_URL%"
endlocal & set "DATABASE_URL=%OLD_DBURL%"

%PYTHON_CMD% -m alembic downgrade base || (
  echo [WARN] Alembic downgrade failed or not initialized for this DB; continuing to file removal
)

echo Deleting DB file: %DB_FILE%
del /f /q "%DB_FILE%" >nul 2>&1 || (
  echo [ERROR] Failed to delete DB file: %DB_FILE%
  exit /b 1
)

echo [SUCCESS] SQLite DB file removed: %DB_FILE%
endlocal
exit /b 0
