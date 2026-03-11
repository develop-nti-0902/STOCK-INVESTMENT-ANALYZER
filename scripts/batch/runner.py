"""batch/runner.py

日時バッチ用の簡易ランナー。以下のモジュールを順次 `python -m` で実行します:
- scripts.batch.batch_fetch_stock_master
- scripts.batch.batch_fetch_stock_prices
- scripts.batch.batch_fetch_edinet_data
- scripts.batch.batch_run_screening

スケジューラ（Windows タスクスケジューラや cron）からこのモジュールを呼び出してください。
例: `poetry run python -m scripts.batch.runner`
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Sequence

JOBS: Sequence[str] = [
    "scripts.batch.batch_fetch_stock_master",
    "scripts.batch.batch_fetch_stock_prices",
    "scripts.batch.batch_fetch_edinet_data",
    "scripts.batch.batch_run_screening",
]


def run_job(module: str) -> int:
    """指定したモジュールを現在の Python 実行環境で `-m` 実行する。

    標準出力 / 標準エラーはログに出す。
    戻り値はプロセスの終了コード。
    """
    cmd = [sys.executable, "-m", module]

    # 一部のバッチは必須引数（例: EDINET の start/end date）を必要とする。
    # 日次運用向けに、EDINETフェッチには前日を start/end に指定する既定動作を入れる。
    if module == "scripts.batch.batch_fetch_edinet_data":
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        # モジュール自体に引数を渡す仕組みがないため、ここでコマンドに追加する
        cmd += ["--start-date", yesterday, "--end-date", yesterday]
    logging.info("Starting job: %s", module)
    logging.debug("Command: %s", " ".join(cmd))

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # ログディレクトリを作成し、モジュール名ごとのログファイルへ追記
    log_dir = Path(__file__).parent / "log"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        logging.exception("Failed to create log directory: %s", log_dir)

    safe_name = module.replace(".", "_")
    logfile = log_dir / f"{safe_name}.log"
    now = datetime.now().isoformat()

    # 毎回上書きする: 実行時刻をファイル先頭に書き込む
    try:
        with logfile.open("w", encoding="utf-8") as f:
            f.write(f"RUN AT: {now}\n")
            f.write("--- COMMAND ---\n")
            f.write("%s\n" % (" ".join(cmd)))
            f.write("--- EXIT CODE ---\n")
            f.write("%s\n" % proc.returncode)
            f.write("--- STDOUT ---\n")
            if proc.stdout:
                f.write(proc.stdout)
            f.write("\n--- STDERR ---\n")
            if proc.stderr:
                f.write(proc.stderr)
            f.write("\n")
    except Exception:
        logging.exception("Failed to write job log for %s", module)

    # 重要な出力はコンソールにも表示
    if proc.stdout:
        logging.info(proc.stdout)
    if proc.stderr:
        logging.error(proc.stderr)

    logging.info("Job %s finished with exit code %d", module, proc.returncode)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch runner: execute batch modules sequentially")
    parser.add_argument("--dry-run", action="store_true", help="各ジョブを実行せずにログのみ出す")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="ジョブが失敗しても次のジョブを継続する",
    )
    parser.add_argument(
        "--jobs",
        nargs="*",
        help="実行するジョブのモジュール名一覧（デフォルトは組み込みジョブ）",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    jobs = args.jobs if args.jobs else list(JOBS)

    logging.info(
        "Batch runner start. jobs=%s dry_run=%s continue_on_error=%s",
        jobs,
        args.dry_run,
        args.continue_on_error,
    )

    for module in jobs:
        if args.dry_run:
            logging.info("(dry-run) would run: %s", module)
            continue

        rc = run_job(module)
        if rc != 0:
            logging.error("Job %s failed with exit code %d", module, rc)
            if not args.continue_on_error:
                logging.info("Stopping remaining jobs due to failure")
                return rc

    logging.info("All jobs finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
