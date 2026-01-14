@echo off
chcp 65001 >nul 2>&1
REM =============================================================================
REM PostgreSQL development database teardown with Alembic (Windows)
REM Location: scripts\databaseSetup\teardown_db.bat
REM Usage: Run this script directly or call it from other setup scripts
REM NOTE: Save this file as UTF-8 without BOM. A BOM can be interpreted as commands by CMD.
REM
REM このスクリプトはAlembicマイグレーションを使用してデータベースをダウングレードし、
 REM 最終的にデータベース、ユーザー、テーブルスペースを削除します。
REM =============================================================================

setlocal enabledelayedexpansion

REM This script first applies Alembic downgrade (alembic downgrade base),
REM then drops the database, user, and tablespace.

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\\..") do set REPO_ROOT=%%~fI\

REM 従来のDROP SQLファイル（非推奨、参考用として保持）
REM set DROP_USER_SQL=%SCRIPT_DIR%sql\drop_user_tables.sql

REM Configuration priority (highest to lowest):
REM 1) Positional arguments: PGHOST PGPORT PGUSER PGPASSWORD DB_NAME DB_USER
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
            if /I "%%~A"=="DB_NAME" if not defined DB_NAME set "DB_NAME=%%~B"
            if /I "%%~A"=="DB_USER" if not defined DB_USER set "DB_USER=%%~B"
            if /I "%%~A"=="DB_DATA_DIR" if not defined DB_DATA_DIR set "DB_DATA_DIR=%%~B"
            if /I "%%~A"=="SKIP_TABLESPACE" if not defined SKIP_TABLESPACE set "SKIP_TABLESPACE=%%~B"
        )
    )
)

REM Positional arguments override other settings (highest priority). Example usage:
REM teardown_db.bat PGHOST PGPORT PGUSER PGPASSWORD DB_NAME DB_USER
if not "%ARG1%"=="" set PGHOST=%ARG1%
if not "%ARG2%"=="" set PGPORT=%ARG2%
if not "%ARG3%"=="" set PGUSER=%ARG3%
if not "%ARG4%"=="" set PGPASSWORD=%ARG4%
if not "%ARG5%"=="" set DB_NAME=%ARG5%
if not "%ARG6%"=="" set DB_USER=%ARG6%
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
echo [INFO] This teardown will DROP the entire database. Individual table drops are skipped.

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
if not defined DB_NAME (
    echo [ERROR] DB_NAME not set. Provide via .env, environment, or fifth positional argument.
    exit /b 1
)
if not defined DB_USER (
    echo [ERROR] DB_USER not set. Provide via .env, environment, or sixth positional argument.
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
echo [3/6] Running Alembic downgrade (if database exists)...

cd "%REPO_ROOT%"

REM Pythonの仮想環境を探す
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD=venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

psql -U %PGUSER% -h %PGHOST% -t -c "SELECT 1 FROM pg_database WHERE datname='!DB_NAME!';" > "%TEMP%\db_check.txt" 2>&1
set /p DB_EXISTS=<"%TEMP%\db_check.txt"
set "DB_EXISTS=%DB_EXISTS: =%"

if "%DB_EXISTS%"=="1" (
    echo Database !DB_NAME! exists, running Alembic downgrade...
    !PYTHON_CMD! -m alembic downgrade base 2>nul || echo [WARN] Alembic downgrade failed or not initialized

    REM 接続を切断してから削除
    psql -U %PGUSER% -h %PGHOST% -c "REVOKE CONNECT ON DATABASE \"!DB_NAME!\" FROM public;" 2>NUL || echo [WARN] Could not revoke connects
    psql -U %PGUSER% -h %PGHOST% -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '!DB_NAME!' AND pid <> pg_backend_pid();" 2>NUL || echo [WARN] Could not terminate connections
    psql -U %PGUSER% -h %PGHOST% -c "DROP DATABASE IF EXISTS \"!DB_NAME!\";" 2>"%TEMP%\db_drop_err.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to drop database !DB_NAME!
        exit /b 1
    )
    echo Database !DB_NAME! dropped successfully
) else (
    echo Database !DB_NAME! does not exist; skipping drop
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
    set "DB_FULL_PATH=!DB_DATA_DIR!\!DB_NAME!"
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

echo Attempting to drop user %DB_USER%...
psql -U %PGUSER% -h %PGHOST% -c "DO $$ BEGIN IF EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '%DB_USER%') THEN ALTER ROLE %DB_USER% WITH NOLOGIN; DROP OWNED BY %DB_USER% CASCADE; DROP ROLE IF EXISTS %DB_USER%; RAISE NOTICE 'User dropped'; ELSE RAISE NOTICE 'User does not exist'; END IF; END$$;" 2>nul
if not errorlevel 1 (
    echo User dropped or did not exist
) else (
    echo [WARN] Could not drop user (may need superuser privileges)
)

endlocal

echo.
echo ========================================
echo [SUCCESS] Database teardown completed!
echo ========================================
echo Database: %DB_NAME%
echo Schema: Downgraded via Alembic (base)
echo.
echo [NOTE] SQL files in sql/ directory are kept for reference only.
echo        All schema changes are now managed through Alembic.
echo ========================================
exit /b 0
