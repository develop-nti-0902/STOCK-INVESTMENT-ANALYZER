#!/usr/bin/env python3
"""チェックを実行してコミットステータスを出力するラッパーです。

処理の流れ:
1) 指定されたチェック（black/isort/flake8/mypy/pylint/pytest）を実行します。
2) 失敗時はステータスファイルを保存し、必要であれば自動修正を行います。
3) 各チェック終了後に "Commit status after <check>: <SUCCESS/FAIL>" を出力します。
4) チェックに失敗があれば非ゼロで終了します。

ステータスファイル: .git/.precommit_status.json
このファイルは各チェックの pass/fail と全体の failed 状態を保持します。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# リポジトリルートを特定（このスクリプトは scripts/hooks/ 配下に置かれる想定）
REPO_ROOT = Path(__file__).resolve().parents[2]
STATUS_FILE = REPO_ROOT / ".git" / ".precommit_status.json"


def load_status() -> Dict[str, Any]:
    # ステータスファイルを読み込み、存在しなければ初期化
    if STATUS_FILE.exists():
        try:
            with STATUS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # 最低限の構造保証
            if (
                not isinstance(data, dict)
                or "checks" not in data
                or "failed" not in data
            ):
                raise ValueError("invalid status json")
            return data
        except (json.JSONDecodeError, OSError, ValueError):
            # 読み込みエラーや不正な構造は無視して初期化を返す
            pass
    return {"checks": [], "failed": False}


def save_status(status: Dict[str, Any]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATUS_FILE.open("w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def set_check_result(status: Dict[str, Any], name: str, passed: bool) -> None:
    """Update or append check result by name."""
    checks = status.setdefault("checks", [])
    for c in checks:
        if c.get("name") == name:
            c["passed"] = passed
            return
    checks.append({"name": name, "passed": passed})


def print_commit_status_after(check_name: str, status: Dict[str, Any]) -> None:
    # 現時点で一つでも失敗があれば、このコミットは失敗扱い
    overall = "FAIL" if status.get("failed") else "SUCCESS"
    print(f"Commit status after {check_name}: {overall}")


def run(cmd: List[str]) -> int:
    # 標準出力/標準エラーはそのまま継承して表示
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print(f"Command not found: {' '.join(cmd)}")
        return 127


def run_black(
    args: List[str], files: List[str], status: Dict[str, Any]
) -> int:
    # まず --check で判定し、必要なら実フォーマットを実施
    cmd_check = [sys.executable, "-m", "black", "--check", *args, *files]
    rc_check = run(cmd_check)
    if rc_check != 0:
        # 自動修正を実施
        cmd_fix = [sys.executable, "-m", "black", *args, *files]
        _ = run(cmd_fix)
        set_check_result(status, "black", False)
        status["failed"] = True
        save_status(status)
        print_commit_status_after("black", status)
        # blackが修正した場合はコミット失敗（pre-commit標準挙動に合わせる）
        return 1

    set_check_result(status, "black", True)
    save_status(status)
    print_commit_status_after("black", status)
    return 0


def run_isort(
    args: List[str], files: List[str], status: Dict[str, Any]
) -> int:
    cmd_check = [sys.executable, "-m", "isort", "--check-only", *args, *files]
    rc_check = run(cmd_check)
    if rc_check != 0:
        # 自動修正
        cmd_fix = [sys.executable, "-m", "isort", *args, *files]
        _ = run(cmd_fix)
        set_check_result(status, "isort", False)
        status["failed"] = True
        save_status(status)
        print_commit_status_after("isort", status)
        return 1

    set_check_result(status, "isort", True)
    save_status(status)
    print_commit_status_after("isort", status)
    return 0


def run_flake8(
    args: List[str], files: List[str], status: Dict[str, Any]
) -> int:
    # flake8 が hooks 自身を解析して pyflakes の互換性問題を起こす場合があるため
    # デフォルトで scripts/hooks を除外する。ユーザーが明示的に --exclude を渡した
    # 場合はその指定を尊重する。
    effective_args = list(args)
    if not any(a.startswith("--exclude") for a in args):
        effective_args.insert(0, "--exclude=scripts/hooks")

    # pre-commit は対象ファイルを個別に渡してくるため、明示的に
    # `scripts/hooks` 配下のファイルが含まれている場合はそれらを除外する。
    filtered_files: List[str] = []
    for f in files:
        try:
            rel = Path(f).resolve().relative_to(REPO_ROOT)
        except ValueError:
            # relative_to が失敗したらファイルは別パスなので除外せず追加
            filtered_files.append(f)
            continue

        # scripts/hooks 以下であれば除外
        if (
            len(rel.parts) >= 2
            and rel.parts[0] == "scripts"
            and (rel.parts[1] == "hooks")
        ):
            continue

        filtered_files.append(f)

    if not filtered_files:
        # 対象ファイルが無ければ flake8 をスキップ
        print(
            "Skipping flake8: only files under scripts/hooks would be checked."
        )
        rc = 0
    else:
        cmd = [
            sys.executable,
            "-m",
            "flake8",
            *effective_args,
            *filtered_files,
        ]
        rc = run(cmd)
    set_check_result(status, "flake8", rc == 0)
    if rc != 0:
        status["failed"] = True
    save_status(status)
    print_commit_status_after("flake8", status)
    return rc


def run_mypy(args: List[str], files: List[str], status: Dict[str, Any]) -> int:
    # mypyにもターゲット（ディレクトリ/ファイル）を渡す
    cmd = [sys.executable, "-m", "mypy", *args, *files]
    rc = run(cmd)
    set_check_result(status, "mypy", rc == 0)
    if rc != 0:
        status["failed"] = True
    save_status(status)
    print_commit_status_after("mypy", status)
    return rc


def run_pylint(
    args: List[str], files: List[str], status: Dict[str, Any]
) -> int:
    # pylint を実行（ファイル指定があればそのファイル群を対象に）
    cmd = [sys.executable, "-m", "pylint", *args, *files]
    rc = run(cmd)
    set_check_result(status, "pylint", rc == 0)
    if rc != 0:
        status["failed"] = True
    save_status(status)
    print_commit_status_after("pylint", status)
    return rc


def run_pytest(
    args: List[str], files: List[str], status: Dict[str, Any]
) -> int:
    # pytest は通常テスト全体を回すため、ファイル指定が無ければツール引数のみで実行
    # pre-commit 設定で pass_filenames: false にすることを推奨
    cmd = [sys.executable, "-m", "pytest", *args]
    if files:
        # ファイルが渡されている場合はそれをテストターゲットとして渡す
        cmd = [sys.executable, "-m", "pytest", *args, *files]
    # 出力をキャプチャして "collected 0 items" を検出できるようにする
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    # pytest の出力をそのまま表示
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)

    rc = proc.returncode
    # pytest の exit code 5 は "no tests collected" の場合に返されることがある
    # テストが存在しないプロジェクトで pre-commit を通すため、"collected 0 items" が
    # 出力に含まれている場合は成功扱いとする。
    if rc == 5:
        output = (proc.stdout or "") + (proc.stderr or "")
        if "collected 0 items" in output or "collected 0" in output:
            rc = 0
            print("No tests collected; treating pytest as SUCCESS")

    set_check_result(status, "pytest", rc == 0)
    if rc != 0:
        status["failed"] = True
    save_status(status)
    print_commit_status_after("pytest", status)
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run check and print commit status"
    )
    parser.add_argument(
        "--check",
        required=True,
        choices=["black", "isort", "flake8", "mypy", "pylint", "pytest"],
        help="Which check to run",
    )
    # 追加の引数は未知のオプションも許容して取得する
    known_args, extra = parser.parse_known_args()

    # ステータスを読み込み（最初の黒フック時にリセット）
    status = load_status()
    if known_args.check == "black":
        status = {"checks": [], "failed": False}
        save_status(status)

    # pre-commitからの未知引数にはツールオプションとファイルパスが混在
    files: List[str] = []
    tool_args: List[str] = []
    for token in extra:
        # ファイルと思われるものとオプションの分離
        p = Path(token)
        if p.exists():
            files.append(token)
        else:
            tool_args.append(token)

    rc = 2
    if known_args.check == "black":
        rc = run_black(tool_args, files, status)
    if known_args.check == "isort":
        rc = run_isort(tool_args, files, status)
    if known_args.check == "flake8":
        rc = run_flake8(tool_args, files, status)
    if known_args.check == "mypy":
        # mypyにもファイル/ディレクトリを渡す
        rc = run_mypy(tool_args, files, status)
    if known_args.check == "pylint":
        rc = run_pylint(tool_args, files, status)
    if known_args.check == "pytest":
        rc = run_pytest(tool_args, files, status)
    if rc == 2:
        print(f"Unsupported check: {known_args.check}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
