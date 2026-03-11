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
    # 一部のバッチは複数回呼び出す（例: 日足と分足を別々に取得）
    # 特別扱い: batch_fetch_stock_prices は timeframe を変えて 1d と 1m を順次実行する
    log_dir = Path(__file__).parent / "log"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        logging.exception("Failed to create log directory: %s", log_dir)

    results: list[int] = []

    if module == "scripts.batch.batch_fetch_stock_prices":
        timeframes = ("1d", "1m")
        for tf in timeframes:
            cmd = [sys.executable, "-m", module, "--timeframe", tf]
            logging.info("Starting job: %s timeframe=%s", module, tf)
            logging.debug("Command: %s", " ".join(cmd))

            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            safe_name = f"{module.replace('.', '_')}_{tf}"
            logfile = log_dir / f"{safe_name}.log"
            now = datetime.now().isoformat()

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
                logging.exception("Failed to write job log for %s", safe_name)

            if proc.stdout:
                logging.info(proc.stdout)
            if proc.stderr:
                logging.error(proc.stderr)

            logging.info(
                "Job %s timeframe=%s finished with exit code %d", module, tf, proc.returncode
            )
            results.append(proc.returncode)

        # いずれかが失敗していれば非ゼロを返す
        return 0 if all(rc == 0 for rc in results) else 1

    # 通常の単発ジョブ実行
    cmd = [sys.executable, "-m", module]

    # EDINET の既定引数を付与
    if module == "scripts.batch.batch_fetch_edinet_data":
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        cmd += ["--start-date", yesterday, "--end-date", yesterday]

    logging.info("Starting job: %s", module)
    logging.debug("Command: %s", " ".join(cmd))

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    safe_name = module.replace(".", "_")
    logfile = log_dir / f"{safe_name}.log"
    now = datetime.now().isoformat()

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
