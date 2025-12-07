@echo off
chcp 65001 >nul 2>&1
REM =============================================================================
REM Alembic migration wrapper (Windows)
REM Location: scripts\databaseSetup\migrate.bat
REM Usage: migrate.bat [upgrade|downgrade|history|current] [<target>] [--sql]
REM =============================================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\..") do set REPO_ROOT=%%~fI\

REM Load .env if present
if exist "%REPO_ROOT%.env" (
  echo [INFO] Loading env from %REPO_ROOT%.env
  for /f "usebackq tokens=1* delims==" %%A in ("%REPO_ROOT%.env") do (
    if not "%%A"=="" (
      if /I "%%~A"=="DATABASE_URL" if not defined DATABASE_URL set "DATABASE_URL=%%~B"
      if /I "%%~A"=="PGHOST" if not defined PGHOST set "PGHOST=%%~B"
      if /I "%%~A"=="PGPORT" if not defined PGPORT set "PGPORT=%%~B"
      if /I "%%~A"=="DB_NAME" if not defined DB_NAME set "DB_NAME=%%~B"
      if /I "%%~A"=="DB_USER" if not defined DB_USER set "DB_USER=%%~B"
      if /I "%%~A"=="DB_PASSWORD" if not defined DB_PASSWORD set "DB_PASSWORD=%%~B"
    )
  )
)

REM Parse args
if "%~1"=="" (
  echo Usage: %~nx0 [upgrade^|downgrade^|history^|current] [<target>] [--sql]
  exit /b 1
)

set CMD=%~1
set TARGET=%~2
if "%TARGET%"=="" set TARGET=head
set SQL_FLAG=
if "%~3"=="--sql" set SQL_FLAG=--sql

echo [INFO] Running alembic command: %CMD% %TARGET% %SQL_FLAG%

REM Construct DATABASE_URL if necessary
if not defined DATABASE_URL (
  if defined PGHOST if defined PGPORT if defined DB_NAME if defined DB_USER if defined DB_PASSWORD (
    set "DATABASE_URL=postgresql://%DB_USER%:%DB_PASSWORD%@%PGHOST%:%PGPORT%/%DB_NAME%"
    echo [INFO] Constructed DATABASE_URL from environment variables
  )
)

where poetry >nul 2>&1
if errorlevel 1 (
  echo [WARN] poetry not found in PATH; attempting to run alembic directly
  set ALEMBIC_CMD=alembic -c "%REPO_ROOT%alembic.ini" %CMD% %TARGET% %SQL_FLAG%
  echo [INFO] %ALEMBIC_CMD%
  %ALEMBIC_CMD%
) else (
  poetry run alembic -c "%REPO_ROOT%alembic.ini" %CMD% %TARGET% %SQL_FLAG%
)

endlocal
echo [SUCCESS] alembic command finished
exit /b 0
