#!/usr/bin/env python3
"""app配下のソースファイルに対するユニットテストの存在をチェックするツールです.

処理の流れ:
1) app配下のすべてのPythonファイル（__init__.py, __pycache__を除く）を走査します。
2) 各ファイルに対応するtests/unit/のテストファイル（test_<ファイル名>）が存在するかチェックします。
3) ユニットテストが不足しているファイルや命名規約が異なるファイルをレポートします。
4) 問題がある場合は非ゼロで終了します。

命名規約: test_<ソース名>.py
例: app/services/stock_service.py -> tests/unit/services/test_stock_service.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# リポジトリルートを特定（このスクリプトは scripts/hooks/ 配下に置かれる想定）
REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"
TESTS_UNIT_DIR = REPO_ROOT / "tests" / "unit"

# チェック対象外とするファイル名
EXCLUDE_FILES = {"__init__.py", "main.py", "templates_config.py"}

# チェック対象外とするディレクトリ名
EXCLUDE_DIRS = {"__pycache__", "static", "templates"}


def find_python_files(directory: Path) -> List[Path]:
    """指定ディレクトリ配下のPythonファイルを再帰的に検索します.

    Args:
        directory: 検索対象のディレクトリ

    Returns:
        Pythonファイルのパスのリスト
    """
    python_files = []
    for file_path in directory.rglob("*.py"):
        # 除外対象のディレクトリをスキップ
        if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
            continue
        # 除外対象のファイルをスキップ
        if file_path.name in EXCLUDE_FILES:
            continue
        python_files.append(file_path)
    return python_files


def get_expected_test_path(source_file: Path) -> Path:
    """ソースファイルに対応する期待されるテストファイルのパスを返します.

    Args:
        source_file: app配下のソースファイルパス

    Returns:
        tests/unit配下の期待されるテストファイルパス
    """
    # app配下の相対パスを取得
    relative_path = source_file.relative_to(APP_DIR)

    # ディレクトリ部分とファイル名を分離
    directory = relative_path.parent
    filename = relative_path.name

    # test_プレフィックスを追加
    test_filename = f"test_{filename}"

    # tests/unit配下の対応するパスを構築
    expected_test_path = TESTS_UNIT_DIR / directory / test_filename

    return expected_test_path


def get_expected_source_path(test_file: Path) -> Path:
    """テストファイルに対応する期待されるソースファイルのパスを返します.

    Args:
        test_file: tests/unit配下のテストファイルパス

    Returns:
        app配下の期待されるソースファイルパス
    """
    # tests/unit配下の相対パスを取得
    relative_path = test_file.relative_to(TESTS_UNIT_DIR)

    # ディレクトリ部分とファイル名を分離
    directory = relative_path.parent
    filename = relative_path.name

    # test_プレフィックスを除去
    if filename.startswith("test_"):
        source_filename = filename[5:]  # "test_"を除去
    else:
        # test_で始まらない場合はそのまま（エラーケース）
        source_filename = filename

    # app配下の対応するパスを構築
    expected_source_path = APP_DIR / directory / source_filename

    return expected_source_path


def find_misnamed_test_files(test_dir: Path, expected_test_file: Path) -> List[Path]:
    """命名規約に従っていないテストファイルを検索します.

    Args:
        test_dir: テストファイルがあるべきディレクトリ
        expected_test_file: 期待されるテストファイル名

    Returns:
        命名規約に従っていないテストファイルのリスト
    """
    if not test_dir.exists():
        return []

    misnamed_files = []
    expected_filename = expected_test_file.name

    # ディレクトリ内の.pyファイルを検索
    for file_path in test_dir.glob("*.py"):
        # __init__.pyは除外
        if file_path.name == "__init__.py":
            continue

        # 期待されるファイル名と異なり、かつtest_で始まらない場合は命名違反
        if file_path.name != expected_filename and not file_path.name.startswith("test_"):
            misnamed_files.append(file_path)

    return misnamed_files


def check_orphaned_tests() -> List[Path]:
    """対応するソースファイルが存在しないテストファイル（孤立したテスト）を検出します.

    Returns:
        対応するソースファイルが存在しないテストファイルのリスト
    """
    orphaned_tests = []

    # tests/unit配下のPythonファイルを取得
    if not TESTS_UNIT_DIR.exists():
        return orphaned_tests

    test_files = find_python_files(TESTS_UNIT_DIR)

    for test_file in sorted(test_files):
        # test_で始まらないファイルはスキップ（命名規約違反として別途検出される）
        if not test_file.name.startswith("test_"):
            continue

        # 期待されるソースファイルのパスを取得
        expected_source_file = get_expected_source_path(test_file)

        # ソースファイルの存在をチェック
        if not expected_source_file.exists():
            orphaned_tests.append(test_file)

    return orphaned_tests


def check_test_coverage() -> Tuple[List[Path], List[Tuple[Path, List[Path]]], List[Path]]:
    """app配下のソースファイルに対するテストカバレッジをチェックします.

    Returns:
        (テストが不足しているファイルのリスト, 命名違反のファイルのリスト, 孤立したテストのリスト)
    """
    missing_tests = []
    misnamed_tests = []

    # app配下のPythonファイルを取得
    source_files = find_python_files(APP_DIR)

    print(f"app配下のソースファイルをチェック中... (合計: {len(source_files)}ファイル)")
    print()

    for source_file in sorted(source_files):
        # 期待されるテストファイルのパスを取得
        expected_test_file = get_expected_test_path(source_file)

        # テストファイルの存在をチェック
        if not expected_test_file.exists():
            missing_tests.append(source_file)
        else:
            # 命名違反のファイルをチェック
            test_dir = expected_test_file.parent
            misnamed = find_misnamed_test_files(test_dir, expected_test_file)
            if misnamed:
                misnamed_tests.append((source_file, misnamed))

    # 孤立したテストをチェック
    print("tests/unit配下のテストファイルをチェック中...")
    print()
    orphaned_tests = check_orphaned_tests()

    return missing_tests, misnamed_tests, orphaned_tests


def print_report(
    missing_tests: List[Path],
    misnamed_tests: List[Tuple[Path, List[Path]]],
    orphaned_tests: List[Path],
    total_files: int,
) -> None:
    """チェック結果のレポートを出力します.

    Args:
        missing_tests: テストが不足しているファイルのリスト
        misnamed_tests: 命名違反のファイルのリスト
        orphaned_tests: 孤立したテストのリスト
        total_files: チェック対象のファイル総数
    """
    has_issues = False

    # 統計情報を表示
    tested_files = total_files - len(missing_tests)
    coverage_rate = (tested_files / total_files * 100) if total_files > 0 else 0

    print("=" * 80)
    print("📊 統計情報")
    print("=" * 80)
    print(f"  チェック対象ファイル数: {total_files}")
    print(f"  テスト済みファイル数: {tested_files}")
    print(f"  テスト不足ファイル数: {len(missing_tests)}")
    print(f"  孤立したテスト数: {len(orphaned_tests)}")
    print(f"  テストカバレッジ率: {coverage_rate:.1f}%")
    print()

    if missing_tests:
        has_issues = True
        print("=" * 80)
        print("❌ ユニットテストが不足しているファイル")
        print("=" * 80)

        # レイヤー別にグループ化
        grouped_by_layer: Dict[str, List[Path]] = defaultdict(list)
        for source_file in missing_tests:
            relative_path = source_file.relative_to(APP_DIR)
            # 最上位のディレクトリをレイヤーとみなす
            layer = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"
            grouped_by_layer[layer].append(source_file)

        # レイヤー別に表示
        for layer in sorted(grouped_by_layer.keys()):
            layer_files = grouped_by_layer[layer]
            print(f"\n📁 {layer.upper()} レイヤー ({len(layer_files)}ファイル)")
            print("-" * 80)

            for source_file in sorted(layer_files):
                relative_source = source_file.relative_to(APP_DIR)
                expected_test = get_expected_test_path(source_file).relative_to(REPO_ROOT)
                print(f"  ✗ {relative_source}")
                print(f"    → 期待されるテスト: {expected_test}")
                print()

    if orphaned_tests:
        has_issues = True
        print("=" * 80)
        print("🚨 規約に則っていない場所に作成されたテストファイル")
        print("=" * 80)
        print("以下のテストファイルに対応するソースファイルが存在しません。")
        print()

        # レイヤー別にグループ化
        grouped_by_layer: Dict[str, List[Path]] = defaultdict(list)
        for test_file in orphaned_tests:
            relative_path = test_file.relative_to(TESTS_UNIT_DIR)
            # 最上位のディレクトリをレイヤーとみなす
            layer = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"
            grouped_by_layer[layer].append(test_file)

        # レイヤー別に表示
        for layer in sorted(grouped_by_layer.keys()):
            layer_files = grouped_by_layer[layer]
            print(f"📁 {layer.upper()} レイヤー ({len(layer_files)}ファイル)")
            print("-" * 80)

            for test_file in sorted(layer_files):
                relative_test = test_file.relative_to(TESTS_UNIT_DIR)
                expected_source = get_expected_source_path(test_file).relative_to(REPO_ROOT)
                print(f"  ✗ tests/unit/{relative_test}")
                print(f"    → 期待されるソース: {expected_source} (存在しません)")
                print()

    if misnamed_tests:
        has_issues = True
        print("=" * 80)
        print("⚠️  命名規約に従っていない可能性のあるテストファイル")
        print("=" * 80)
        for source_file, misnamed in misnamed_tests:
            relative_source = source_file.relative_to(APP_DIR)
            print(f"  ソース: app/{relative_source}")
            for misnamed_file in misnamed:
                print(f"    - {misnamed_file.relative_to(REPO_ROOT)}")
            print()

    if not has_issues:
        print("=" * 80)
        print("✅ すべてのソースファイルに対応するユニットテストが存在し、命名規約に従っています。")
        print("=" * 80)
        print()
    else:
        print("=" * 80)
        print("📝 命名規約: test_<ソース名>.py")
        print("   例: app/services/stock_service.py -> tests/unit/services/test_stock_service.py")
        print("   ※ テストファイルはapp配下と同じディレクトリ構造である必要があります")
        print("=" * 80)


def main() -> int:
    """メイン処理.

    Returns:
        終了コード（0: 成功, 1: 問題あり）
    """
    print("🔍 ユニットテストカバレッジチェックを開始します...")
    print()

    # チェック実行
    missing_tests, misnamed_tests, orphaned_tests = check_test_coverage()

    # app配下のファイル総数を取得
    total_files = len(find_python_files(APP_DIR))

    # レポート出力
    print_report(missing_tests, misnamed_tests, orphaned_tests, total_files)

    # 問題がある場合は非ゼロで終了
    if missing_tests or misnamed_tests or orphaned_tests:
        print()
        print(f"⚠️  問題が見つかりました:")
        print(f"   - テスト不足: {len(missing_tests)}ファイル")
        print(f"   - 孤立したテスト: {len(orphaned_tests)}ファイル")
        print(f"   - 命名違反の可能性: {len(misnamed_tests)}箇所")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
