@echo off
chcp 65001 >nul 2>&1
REM =============================================================================
REM PostgreSQL development database setup (Windows)
REM Location: scripts\databaseSetup\setup_db.bat
REM Usage: Run this script directly or call it from other setup scripts
REM NOTE: Save this file as UTF-8 without BOM. A BOM can be interpreted as commands by CMD.
REM =============================================================================

setlocal enabledelayedexpansion

REM This script uses the local psql client to create the database and user,
REM and applies the initial schema from `create_stock_tables.sql` and
REM `create_management_tables.sql` if present.

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\\..") do set REPO_ROOT=%%~fI\
set STOCK_SQL=%SCRIPT_DIR%sql\create_stock_tables.sql
set MGMT_SQL=%SCRIPT_DIR%sql\create_management_tables.sql

REM Configuration priority (highest to lowest):
REM 1) Positional arguments: PGHOST PGPORT PGUSER PGPASSWORD DB_NAME DB_USER DB_PASSWORD
REM 2) Environment variables (set or PowerShell $Env:)
REM 3) .env file at repository root (if present)

REM Store positional arguments temporarily to apply them after .env loading
set ARG1=%~1
set ARG2=%~2
set ARG3=%~3
set ARG4=%~4
set ARG5=%~5
set ARG6=%~6
set ARG7=%~7
set ARG8=%~8
set ARG9=%~9

REM Load .env file from the repo root if present.
REM Expected file: %REPO_ROOT%.env (e.g. F:\...\.env)
if exist "%REPO_ROOT%.env" (
    echo [INFO] Loading env from %REPO_ROOT%.env
    for /f "usebackq tokens=1* delims==" %%A in ("%REPO_ROOT%.env") do (
        if not "%%A"=="" (
            if /I "%%~A"=="PGHOST" if not defined PGHOST set "PGHOST=%%~B"
            if /I "%%~A"=="PGPORT" if not defined PGPORT set "PGPORT=%%~B"
            if /I "%%~A"=="PGUSER" if not defined PGUSER set "PGUSER=%%~B"
            if /I "%%~A"=="PGPASSWORD" if not defined PGPASSWORD set "PGPASSWORD=%%~B"
            if /I "%%~A"=="DB_NAME" if not defined DB_NAME set "DB_NAME=%%~B"
            if /I "%%~A"=="DB_USER" if not defined DB_USER set "DB_USER=%%~B"
            if /I "%%~A"=="DB_PASSWORD" if not defined DB_PASSWORD set "DB_PASSWORD=%%~B"
            if /I "%%~A"=="DB_DATA_DIR" if not defined DB_DATA_DIR set "DB_DATA_DIR=%%~B"
            if /I "%%~A"=="SKIP_TABLESPACE" if not defined SKIP_TABLESPACE set "SKIP_TABLESPACE=%%~B"
        )
    )
)

REM Positional arguments override other settings (highest priority). Example usage:
REM setup_db.bat PGHOST PGPORT PGUSER PGPASSWORD DB_NAME DB_USER DB_PASSWORD
if not "%ARG1%"=="" set PGHOST=%ARG1%
if not "%ARG2%"=="" set PGPORT=%ARG2%
if not "%ARG3%"=="" set PGUSER=%ARG3%
if not "%ARG4%"=="" set PGPASSWORD=%ARG4%
if not "%ARG5%"=="" set DB_NAME=%ARG5%
if not "%ARG6%"=="" set DB_USER=%ARG6%
if not "%ARG7%"=="" set DB_PASSWORD=%ARG7%
REM 8th argument: DB_DATA_DIR (or boolean to indicate SKIP_TABLESPACE).
REM If the 8th arg is 1/TRUE/YES then SKIP_TABLESPACE is set and DB_DATA_DIR is cleared.
if not "%ARG8%"=="" (
    if /I "%ARG8%"=="1" (
        set SKIP_TABLESPACE=%ARG8%
        set DB_DATA_DIR=
    ) else if /I "%ARG8%"=="TRUE" (
        set SKIP_TABLESPACE=%ARG8%
        set DB_DATA_DIR=
    ) else if /I "%ARG8%"=="YES" (
        set SKIP_TABLESPACE=%ARG8%
        set DB_DATA_DIR=
    ) else (
        set DB_DATA_DIR=%ARG8%
        set SKIP_TABLESPACE=
        if not "%ARG9%"=="" set SKIP_TABLESPACE=%ARG9%
    )
)


echo.
echo ========================================
echo Database setup (Windows)
echo ========================================
echo.

REM Check for psql in PATH
echo [1/6] Checking PostgreSQL installation...

where psql >nul 2>&1
if errorlevel 1 (
    echo [ERROR] psql ^(PostgreSQL client^) not found in PATH.
    echo Install PostgreSQL client or add it to PATH, then retry.
    exit /b 1
)

echo Using PGHOST=%PGHOST% PGPORT=%PGPORT% PGUSER=%PGUSER%

echo Creating database and user (may ask for postgres password)...

REM Validate required variables
echo [2/6] Validating required variables...

if not defined PGHOST (
    echo [ERROR] PGHOST not set. Provide via .env, environment, or first positional argument.
    exit /b 1
)
if not defined PGPORT (
    echo [ERROR] PGPORT not set. Provide via .env, environment, or second positional argument.
    exit /b 1
)
if not defined PGUSER (
    echo [ERROR] PGUSER not set. Provide via .env, environment, or third positional argument.
    exit /b 1
)
if not defined DB_NAME (
    echo [ERROR] DB_NAME not set. Provide via .env, environment, or fifth positional argument.
    exit /b 1
)
if not defined DB_USER (
    echo [ERROR] DB_USER not set. Provide via .env, environment, or sixth positional argument.
    exit /b 1
)
if not defined DB_PASSWORD (
    echo [ERROR] DB_PASSWORD not set. Provide via .env, environment, or seventh positional argument.
    exit /b 1
)
if not defined PGPASSWORD (
    echo [ERROR] PGPASSWORD not set. Provide via .env, environment, or fourth positional argument.
    exit /b 1
)
REM Check DB_DATA_DIR vs SKIP_TABLESPACE relationship (string comparisons for robustness)
REM - If DB_DATA_DIR is empty and SKIP_TABLESPACE is empty => error
REM - If DB_DATA_DIR is set and SKIP_TABLESPACE is also non-empty => error
if "%DB_DATA_DIR%"=="" (
    if "%SKIP_TABLESPACE%"=="" (
        echo [ERROR] DB_DATA_DIR not set. Provide via .env, environment, or eighth positional argument.
        exit /b 1
    )
)
if NOT "%DB_DATA_DIR%"=="" (
    if NOT "%SKIP_TABLESPACE%"=="" (
        echo [ERROR] DB_DATA_DIR is set but SKIP_TABLESPACE is also specified; these are mutually exclusive.
        exit /b 1
    )
)

REM Create database user (ignore if exists)
echo [3/6] Creating database user (if not exists)...

psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '%DB_USER%') THEN CREATE USER %DB_USER% WITH PASSWORD '%DB_PASSWORD%'; END IF; END$$;" 2>NUL
if errorlevel 1 echo [WARN] Could not create user (you may need to run as a superuser or provide correct postgres password)

echo [4/6] Preparing tablespace directory and tablespace...
if not "%SKIP_TABLESPACE%"=="" (
    echo [INFO] SKIP_TABLESPACE is set; skipping tablespace and directory creation
    goto :AFTER_TABLESPACE_SETUP
)
set "DB_FULL_PATH=!DB_DATA_DIR!\!DB_NAME!"
    if not exist "!DB_FULL_PATH!" (
        echo Creating directory: !DB_FULL_PATH!
        mkdir "!DB_FULL_PATH!"
        if errorlevel 1 (
            echo [ERROR] Failed to create directory %DB_FULL_PATH%
            exit /b 1
        )
    )

    REM Check for existing tablespace (use temp file to avoid complex for/f parsing issues)
    psql -U %PGUSER% -h %PGHOST% -t -c "SELECT 1 FROM pg_tablespace WHERE spcname='stock_data_space';" > "%TEMP%\ts_check.txt" 2>&1
    set /p TS_CHECK=<"%TEMP%\ts_check.txt"
    set "TS_CHECK=%TS_CHECK: =%"
    if not "%TS_CHECK%"=="1" (
        echo Creating tablespace stock_data_space at !DB_FULL_PATH!
        psql -U %PGUSER% -h %PGHOST% -c "CREATE TABLESPACE stock_data_space OWNER %PGUSER% LOCATION '!DB_FULL_PATH!';" 2>"%TEMP%\ts_create_err.txt"
        if errorlevel 1 echo [WARN] Failed to create tablespace (it may already exist or you may lack privileges)
    ) else (
        echo Tablespace stock_data_space already exists
    )
:AFTER_TABLESPACE_SETUP

REM Check if the database exists; if not, create it
echo [5/6] Creating database if not exists...

psql -U %PGUSER% -h %PGHOST% -t -c "SELECT 1 FROM pg_database WHERE datname='!DB_NAME!';" > "%TEMP%\db_check.txt" 2>&1
set /p DB_EXISTS=<"%TEMP%\db_check.txt"
set "DB_EXISTS=%DB_EXISTS: =%"
if not "%DB_EXISTS%"=="1" (
    if not "%SKIP_TABLESPACE%"=="" (
        REM Create database without tablespace (use default)
        psql -U %PGUSER% -h %PGHOST% -c "CREATE DATABASE !DB_NAME! WITH OWNER = %PGUSER% ENCODING = 'UTF8' LC_COLLATE = 'C' LC_CTYPE = 'C' TEMPLATE = template0 CONNECTION LIMIT = -1;" 2>"%TEMP%\db_create_err.txt"
    ) else (
        REM Create database with custom tablespace
        psql -U %PGUSER% -h %PGHOST% -c "CREATE DATABASE !DB_NAME! WITH OWNER = %PGUSER% ENCODING = 'UTF8' LC_COLLATE = 'C' LC_CTYPE = 'C' TABLESPACE = stock_data_space TEMPLATE = template0 CONNECTION LIMIT = -1;" 2>"%TEMP%\db_create_err.txt"
    )
    if errorlevel 1 (
        echo [ERROR] Failed to create database
        exit /b 1
    )
) else (
    echo Database %DB_NAME% already exists
)

REM Grant privileges
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %DB_NAME% -c "GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %DB_USER%;" 2>NUL || echo [WARN] Could not grant privileges

REM Apply initial schema if present
echo [6/6] Applying initial schema (if present) and finishing...

REM Set client encoding to UTF8 for psql
set PGCLIENTENCODING=UTF8

REM Apply stock tables then management tables if present
if not exist "%STOCK_SQL%" (
    echo [WARN] %STOCK_SQL% not found; skipping stock tables apply
) else (
    echo Applying stock tables schema: %STOCK_SQL%
    psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %DB_NAME% -v db_user=%DB_USER% -f "%STOCK_SQL%"
    if errorlevel 1 echo [WARN] Failed to apply %STOCK_SQL% (check SQL file and permissions)
)

if not exist "%MGMT_SQL%" (
    echo [WARN] %MGMT_SQL% not found; skipping management tables apply
) else (
    echo Applying management tables schema: %MGMT_SQL%
    psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %DB_NAME% -v db_user=%DB_USER% -f "%MGMT_SQL%"
    if errorlevel 1 echo [WARN] Failed to apply %MGMT_SQL% (check SQL file and permissions)
)

endlocal

echo.
echo [SUCCESS] Database setup script finished.
exit /b 0
