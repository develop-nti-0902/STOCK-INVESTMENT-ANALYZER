@echo off
chcp 65001 >nul 2>&1
REM =============================================================================
REM Alembic マイグレーション適用スクリプト (Windows)
REM Location: scripts\databaseSetup\migrate.bat
REM
REM このスクリプトは既存のデータベースに対してAlembicマイグレーションを適用します。
REM データベースを破棄せずにスキーマ変更（テーブル追加、カラム変更など）を行います。
REM
REM 使用例:
REM   migrate.bat              # 最新バージョンまでマイグレーション
REM   migrate.bat +1           # 1つ先のバージョンにマイグレーション
REM   migrate.bat -1           # 1つ前のバージョンにダウングレード
REM   migrate.bat 4e581533f2e4 # 特定のリビジョンにマイグレーション
REM =============================================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\\..") do set REPO_ROOT=%%~fI\

REM マイグレーションターゲット（デフォルトはhead）
set "MIGRATION_TARGET=head"
if not "%~1"=="" set "MIGRATION_TARGET=%~1"

echo.
echo ========================================
echo Alembic Migration Tool
echo ========================================
echo.

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
echo.

REM 現在のマイグレーション状態を表示
echo [Current migration status]
!PYTHON_CMD! -m alembic current
if errorlevel 1 (
    echo [ERROR] Failed to get current migration status
    echo Please check:
    echo   - Database is running and accessible
    echo   - Connection settings in .env
    echo   - Alembic is installed: !PYTHON_CMD! -m pip install alembic
    exit /b 1
)

echo.
echo [Available migrations]
!PYTHON_CMD! -m alembic history --verbose
echo.

REM ユーザー確認
if /I "%MIGRATION_TARGET%"=="head" (
    echo About to migrate to: LATEST VERSION ^(head^)
) else (
    echo About to migrate to: %MIGRATION_TARGET%
)

set /p CONFIRM="Continue? (y/N): "
if /I not "%CONFIRM%"=="y" (
    echo Migration cancelled
    exit /b 0
)

echo.
echo [Applying migration]

REM ダウングレード判定（-1などの場合）
echo %MIGRATION_TARGET% | findstr /R "^-[0-9]" >nul
if not errorlevel 1 (
    echo Downgrading...
    !PYTHON_CMD! -m alembic downgrade %MIGRATION_TARGET%
) else (
    echo Upgrading...
    !PYTHON_CMD! -m alembic upgrade %MIGRATION_TARGET%
)

if errorlevel 1 (
    echo.
    echo [ERROR] Migration failed
    echo.
    echo Troubleshooting:
    echo   1. Check error message above
    echo   2. Verify database connection
    echo   3. Check migration file syntax
    echo   4. Review alembic/env.py configuration
    echo.
    echo Useful commands:
    echo   !PYTHON_CMD! -m alembic current    # Show current version
    echo   !PYTHON_CMD! -m alembic history    # Show migration history
    echo   !PYTHON_CMD! -m alembic stamp head # Mark as up-to-date without running
    echo.
    exit /b 1
)

echo.
echo [New migration status]
!PYTHON_CMD! -m alembic current

echo.
echo ========================================
echo [SUCCESS] Migration completed!
echo ========================================
echo.

endlocal
exit /b 0
