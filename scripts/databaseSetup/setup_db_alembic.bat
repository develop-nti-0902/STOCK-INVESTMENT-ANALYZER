@echo off
chcp 65001 >nul 2>&1
REM =============================================================================
REM Alembic対応 PostgreSQL データベース初期セットアップスクリプト (Windows)
REM Location: scripts\databaseSetup\setup_db_alembic.bat
REM
REM このスクリプトは以下を実行します:
REM   1. データベースユーザーの作成
REM   2. テーブルスペースの作成（データ配置ディレクトリ指定）
REM   3. データベースの作成
REM   4. 権限の付与
REM   5. Alembicマイグレーションの適用（テーブル作成）
REM
REM 注意: 既存のデータベースを破棄せずにスキーマ変更する場合は migrate.bat を使用してください
REM =============================================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\\..") do set REPO_ROOT=%%~fI\

REM .envファイルから環境変数を読み込み
if exist "%REPO_ROOT%.env" (
    echo [INFO] Loading environment variables from %REPO_ROOT%.env
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
        )
    )
)

echo.
echo ========================================
echo Alembic Database Setup (Windows)
echo ========================================
echo.

REM 必須変数の検証
echo [1/6] Validating required variables...

if not defined PGHOST (
    echo [ERROR] PGHOST not set
    exit /b 1
)
if not defined PGPORT (
    echo [ERROR] PGPORT not set
    exit /b 1
)
if not defined PGUSER (
    echo [ERROR] PGUSER not set
    exit /b 1
)
if not defined PGPASSWORD (
    echo [ERROR] PGPASSWORD not set
    exit /b 1
)
if not defined DB_NAME (
    echo [ERROR] DB_NAME not set
    exit /b 1
)
if not defined DB_USER (
    echo [ERROR] DB_USER not set
    exit /b 1
)
if not defined DB_PASSWORD (
    echo [ERROR] DB_PASSWORD not set
    exit /b 1
)
if not defined DB_DATA_DIR (
    echo [ERROR] DB_DATA_DIR not set
    exit /b 1
)

echo Using PGHOST=%PGHOST% PGPORT=%PGPORT% PGUSER=%PGUSER%
echo Database: %DB_NAME%
echo Data Directory: %DB_DATA_DIR%

REM データベースユーザーの作成
echo [2/6] Creating database user...

psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '%DB_USER%') THEN CREATE USER %DB_USER% WITH PASSWORD '%DB_PASSWORD%'; END IF; END$$;" 2>NUL
if errorlevel 1 (
    echo [WARN] Could not create user (may already exist or need superuser privileges^)
) else (
    echo User %DB_USER% created or already exists
)

REM テーブルスペース用ディレクトリの作成
echo [3/6] Preparing tablespace directory...

set "DB_FULL_PATH=%DB_DATA_DIR%\%DB_NAME%"
if not exist "!DB_FULL_PATH!" (
    echo Creating directory: !DB_FULL_PATH!
    mkdir "!DB_FULL_PATH!" 2>NUL
    if errorlevel 1 (
        echo [ERROR] Failed to create directory !DB_FULL_PATH!
        exit /b 1
    )
) else (
    echo Directory already exists: !DB_FULL_PATH!
)

REM テーブルスペースの作成
echo [4/6] Creating tablespace...

REM テーブルスペース名をDB_NAMEベースで生成
set "TABLESPACE_NAME=stock_data_space_%DB_NAME%"

psql -U %PGUSER% -h %PGHOST% -t -c "SELECT 1 FROM pg_tablespace WHERE spcname='!TABLESPACE_NAME!';" > "%TEMP%\ts_check.txt" 2>&1
set /p TS_CHECK=<"%TEMP%\ts_check.txt"
set "TS_CHECK=%TS_CHECK: =%"

if not "%TS_CHECK%"=="1" (
    echo Creating tablespace !TABLESPACE_NAME! at !DB_FULL_PATH!
    psql -U %PGUSER% -h %PGHOST% -c "CREATE TABLESPACE !TABLESPACE_NAME! OWNER %PGUSER% LOCATION '!DB_FULL_PATH!';" 2>"%TEMP%\ts_create_err.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to create tablespace
        type "%TEMP%\ts_create_err.txt"
        exit /b 1
    )
    echo Tablespace created successfully
) else (
    echo Tablespace !TABLESPACE_NAME! already exists
)

REM データベースの作成
echo [5/6] Creating database...

psql -U %PGUSER% -h %PGHOST% -t -c "SELECT 1 FROM pg_database WHERE datname='%DB_NAME%';" > "%TEMP%\db_check.txt" 2>&1
set /p DB_EXISTS=<"%TEMP%\db_check.txt"
set "DB_EXISTS=%DB_EXISTS: =%"

if not "%DB_EXISTS%"=="1" (
    echo Creating database %DB_NAME% with tablespace !TABLESPACE_NAME!
    psql -U %PGUSER% -h %PGHOST% -c "CREATE DATABASE %DB_NAME% WITH OWNER = %PGUSER% ENCODING = 'UTF8' LC_COLLATE = 'C' LC_CTYPE = 'C' TABLESPACE = !TABLESPACE_NAME! TEMPLATE = template0 CONNECTION LIMIT = -1;" 2>"%TEMP%\db_create_err.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to create database
        type "%TEMP%\db_create_err.txt"
        exit /b 1
    )
    echo Database created successfully
) else (
    echo Database %DB_NAME% already exists
)

REM 権限の付与
echo Granting privileges...

psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %DB_NAME% -c "GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %DB_USER%;" 2>NUL
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %DB_NAME% -c "GRANT ALL PRIVILEGES ON SCHEMA public TO %DB_USER%;" 2>NUL
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %DB_NAME% -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO %DB_USER%;" 2>NUL
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %DB_NAME% -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO %DB_USER%;" 2>NUL

if errorlevel 1 (
    echo [WARN] Could not grant all privileges
) else (
    echo Privileges granted successfully
)

REM Alembicマイグレーションの適用
echo [6/6] Applying Alembic migrations...

cd "%REPO_ROOT%"

REM Pythonの仮想環境を探す
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD=venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

echo Using Python: !PYTHON_CMD!
echo Applying migrations...

!PYTHON_CMD! -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Failed to apply Alembic migrations
    echo Please check:
    echo   - Alembic is installed: !PYTHON_CMD! -m pip install alembic
    echo   - Database connection settings in .env
    echo   - alembic/env.py configuration
    exit /b 1
)

echo Migrations applied successfully

echo.
echo ========================================
echo [SUCCESS] Database setup completed!
echo ========================================
echo.
echo Database: %DB_NAME%
echo Tablespace: !TABLESPACE_NAME!
echo Data Location: !DB_FULL_PATH!
echo.
echo Next steps:
echo   - Run tests: pytest
echo   - Apply future migrations: scripts\databaseSetup\migrate.bat
echo   - Check migration status: !PYTHON_CMD! -m alembic current
echo.

endlocal
exit /b 0
