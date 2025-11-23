@echo off
chcp 65001 >nul 2>&1
REM =============================================================================
REM PostgreSQL development database teardown (Windows)
REM Location: scripts\databaseSetup\teardown_db.bat
REM Usage: Run this script directly or call it from other setup scripts
REM NOTE: Save this file as UTF-8 without BOM. A BOM can be interpreted as commands by CMD.
REM =============================================================================

setlocal enabledelayedexpansion

REM This script uses the local psql client to drop the database, user, and tablespace,
REM and optionally removes the data directory created during setup.

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\\..") do set REPO_ROOT=%%~fI\

REM Configuration priority (highest to lowest):
REM 1) Positional arguments: PGHOST PGPORT PGUSER PGPASSWORD NEW_DB NEW_DB_USER
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
            if /I "%%~A"=="NEW_DB" if not defined NEW_DB set "NEW_DB=%%~B"
            if /I "%%~A"=="NEW_DB_USER" if not defined NEW_DB_USER set "NEW_DB_USER=%%~B"
            if /I "%%~A"=="DB_DATA_DIR" if not defined DB_DATA_DIR set "DB_DATA_DIR=%%~B"
            if /I "%%~A"=="SKIP_TABLESPACE" if not defined SKIP_TABLESPACE set "SKIP_TABLESPACE=%%~B"
        )
    )
)

REM Positional arguments override other settings (highest priority). Example usage:
REM teardown_db.bat PGHOST PGPORT PGUSER PGPASSWORD NEW_DB NEW_DB_USER
if not "%ARG1%"=="" set PGHOST=%ARG1%
if not "%ARG2%"=="" set PGPORT=%ARG2%
if not "%ARG3%"=="" set PGUSER=%ARG3%
if not "%ARG4%"=="" set PGPASSWORD=%ARG4%
if not "%ARG5%"=="" set NEW_DB=%ARG5%
if not "%ARG6%"=="" set NEW_DB_USER=%ARG6%
REM 7th argument: DB_DATA_DIR (or boolean to indicate SKIP_TABLESPACE).
REM If the 7th arg is 1/TRUE/YES then SKIP_TABLESPACE is set and DB_DATA_DIR is cleared.
if not "%ARG7%"=="" (
    if /I "%ARG7%"=="1" (
        set SKIP_TABLESPACE=%ARG7%
        set DB_DATA_DIR=
    ) else if /I "%ARG7%"=="TRUE" (
        set SKIP_TABLESPACE=%ARG7%
        set DB_DATA_DIR=
    ) else if /I "%ARG7%"=="YES" (
        set SKIP_TABLESPACE=%ARG7%
        set DB_DATA_DIR=
    ) else (
        set DB_DATA_DIR=%ARG7%
        set SKIP_TABLESPACE=
        if not "%ARG8%"=="" set SKIP_TABLESPACE=%ARG8%
    )
)


echo.
echo ========================================
echo Database teardown (Windows)
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

echo Dropping database and user (may ask for postgres password)...

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
if not defined NEW_DB (
    echo [ERROR] NEW_DB not set. Provide via .env, environment, or fifth positional argument.
    exit /b 1
)
if not defined NEW_DB_USER (
    echo [ERROR] NEW_DB_USER not set. Provide via .env, environment, or sixth positional argument.
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
        echo [ERROR] DB_DATA_DIR not set. Provide via .env, environment, or seventh positional argument.
        exit /b 1
    )
)
if NOT "%DB_DATA_DIR%"=="" (
    if NOT "%SKIP_TABLESPACE%"=="" (
        echo [ERROR] DB_DATA_DIR is set but SKIP_TABLESPACE is also specified; these are mutually exclusive.
        exit /b 1
    )
)

REM Drop database if exists
echo [3/6] Dropping database if exists...

psql -U %PGUSER% -h %PGHOST% -t -c "SELECT 1 FROM pg_database WHERE datname='!NEW_DB!';" > "%TEMP%\db_check.txt" 2>&1
set /p DB_EXISTS=<"%TEMP%\db_check.txt"
set "DB_EXISTS=%DB_EXISTS: =%"
if "%DB_EXISTS%"=="1" (
    REM Disconnect existing connections before dropping
    psql -U %PGUSER% -h %PGHOST% -c "REVOKE CONNECT ON DATABASE \"!NEW_DB!\" FROM public;" 2>NUL || echo [WARN] Could not revoke connects
    psql -U %PGUSER% -h %PGHOST% -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '!NEW_DB!' AND pid <> pg_backend_pid();" 2>NUL || echo [WARN] Could not terminate connections
    psql -U %PGUSER% -h %PGHOST% -c "DROP DATABASE IF EXISTS \"!NEW_DB!\";" 2>"%TEMP%\db_drop_err.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to drop database !NEW_DB!
        exit /b 1
    )
    echo Database !NEW_DB! dropped successfully
) else (
    echo Database !NEW_DB! does not exist; skipping drop
)

echo [4/6] Dropping tablespace (unless skipped)...
if not "%SKIP_TABLESPACE%"=="" (
    echo [INFO] SKIP_TABLESPACE is set; skipping tablespace drop
    goto :AFTER_TABLESPACE_DROP
)
REM Drop tablespace (use IF EXISTS for simplicity)
echo Attempting to drop tablespace stock_data_space...
psql -U %PGUSER% -h %PGHOST% -c "DROP TABLESPACE IF EXISTS stock_data_space;" 2>nul
if not errorlevel 1 (
    echo Tablespace dropped or did not exist
) else (
    echo [WARN] Could not drop tablespace (may be in use or insufficient privileges)
)
:AFTER_TABLESPACE_DROP

echo [5/6] Removing tablespace directory (if specified)...
if not "%SKIP_TABLESPACE%"=="" (
    echo [INFO] SKIP_TABLESPACE is set; skipping directory removal
    goto :AFTER_DIR_REMOVAL
)
if not "%DB_DATA_DIR%"=="" (
    set "DB_FULL_PATH=!DB_DATA_DIR!\!NEW_DB!"
    if exist "!DB_FULL_PATH!" (
        echo [INFO] DB_DATA_DIR specified: !DB_FULL_PATH!
        echo [INFO] Automatic directory removal is disabled for safety. Remove the directory manually if desired.
        echo [INFO] To remove: rmdir /s /q "!DB_FULL_PATH!"
    ) else (
        echo Directory !DB_FULL_PATH! not found; nothing to remove
    )
) else (
    echo DB_DATA_DIR not provided; no directory to remove
)
:AFTER_DIR_REMOVAL

REM Drop user if exists
echo [6/6] Dropping user (if exists) and finishing...

echo Attempting to drop user %NEW_DB_USER%...
psql -U %PGUSER% -h %PGHOST% -c "DO $$ BEGIN IF EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '%NEW_DB_USER%') THEN ALTER ROLE %NEW_DB_USER% WITH NOLOGIN; DROP OWNED BY %NEW_DB_USER% CASCADE; DROP ROLE IF EXISTS %NEW_DB_USER%; RAISE NOTICE 'User dropped'; ELSE RAISE NOTICE 'User does not exist'; END IF; END$$;" 2>nul
if not errorlevel 1 (
    echo User dropped or did not exist
) else (
    echo [WARN] Could not drop user (may need superuser privileges)
)

endlocal

echo.
echo [SUCCESS] Database teardown script finished.
exit /b 0
