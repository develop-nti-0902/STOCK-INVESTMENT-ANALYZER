#!/usr/bin/env python3
"""最終コミットステータスのサマリを表示します.

`.git/.precommit_status.json` を読み取り、各チェック結果と
"Final commit status: <SUCCESS/FAIL>" を表示します。記録されたチェックに
失敗がある場合は非ゼロで終了し、pre-commit に失敗を通知します。

加えて、pre-commit 実行中に自動修正が行われて作業ツリーに変更が残った
場合は `git diff --name-only` で検出し、その場合もコミットを失敗扱いにします。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATUS_FILE = REPO_ROOT / ".git" / ".precommit_status.json"


def get_modified_files() -> list[str]:
    """Return list of modified files in working tree.

    pre-commit のフックによる自動修正が入った場合、作業ツリーに変更が残る。
    それを `git diff --name-only` で検出して、最終サマリーに反映する。
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return []
        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        return files
    except OSError:
        # git コマンドが存在しない等の環境エラーに対して安全に空リストを返す
        return []


def main() -> int:
    """Print final commit status summary and return exit code.

    Reads the status file written by the check runner and prints a
    concise summary. Returns a non-zero exit code when any check failed
    or when auto-fixes were detected.
    """
    final = "UNKNOWN"
    checks = []
    failed_overall = False
    if STATUS_FILE.exists():
        try:
            with STATUS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            failed_overall = bool(data.get("failed"))
            checks = data.get("checks", [])
        except (json.JSONDecodeError, OSError, ValueError):
            # ステータスファイルが壊れているなどの場合は安全側で失敗扱い
            failed_overall = True
    # 自動修正による変更検出
    modified_files = get_modified_files()
    if modified_files:
        failed_overall = True

    final = "FAIL" if failed_overall else "SUCCESS"

    print("\n=== Commit Status Summary ===")
    if checks:
        for c in checks:
            name = c.get("name", "?")
            passed = c.get("passed")
            state = "PASS" if passed else "FAIL"
            print(f"- {name}: {state}")
    # 自動修正の有無を表示
    if modified_files:
        count = len(modified_files)
        print(f"- Auto-fixes detected: {count} file(s) modified")
        # 多すぎる場合は一覧を省略
        if count <= 10:
            for fn in modified_files:
                print(f"  * {fn}")
    print(f"Final commit status: {final}")
    # 失敗が一つでもあれば、非ゼロ終了にしてpre-commitのヘッダーにFailedを表示させる
    return 1 if failed_overall else 0


if __name__ == "__main__":
    sys.exit(main())
