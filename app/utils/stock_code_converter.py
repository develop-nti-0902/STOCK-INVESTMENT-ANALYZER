"""`stock_master` のコードと EDINET の5桁コードを相互変換するユーティリティモジュール."""

from __future__ import annotations


class StockCodeConverter:
    """`stock_master` のコードと EDINET の5桁コードを相互変換するユーティリティクラス。

    使用例:
        converter = StockCodeConverter()
        edinet = converter.to_edinet('1301')
        original = converter.from_edinet('13010')
    """

    def to_edinet(self, sec_code: str) -> str:
        """stock_master の証券コードを EDINET の5桁コードに変換します。

        ルール:
        - 数字文字列を想定します。
        - 長さが5未満の場合は右側にゼロでパディングして5桁にします（例: '1301' -> '13010'）。
        - 長さが5の場合はそのまま返します。
        - 長さが5を超える場合は右端の5文字を返します。
        """
        if sec_code is None:
            raise ValueError("sec_code is required")
        s = str(sec_code).strip()
        if not s:
            raise ValueError("sec_code is empty")
        # 非数値文字も許容する（末尾パディングは文字をそのまま扱う）
        if len(s) < 5:
            return s.ljust(5, "0")
        if len(s) == 5:
            return s
        return s[-5:]

    def from_edinet(self, edinet_code: str) -> str:
        """EDINET の5桁コードを stock_master の形式に戻します（末尾のゼロを除去）。

        例: '13010' -> '1301'
        """
        if edinet_code is None:
            raise ValueError("edinet_code is required")
        s = str(edinet_code).strip()
        if not s:
            raise ValueError("edinet_code is empty")
        # EDINET 側のコードが必ず数字とは限らないケースを想定し、末尾ゼロのみ除去する
        return s.rstrip("0") or "0"


# シンプルに使えるよう、モジュールレベルで状態を持たないインスタンスとラッパを提供します
_converter = StockCodeConverter()


def to_edinet_code(sec_code: str) -> str:
    """`stock_master` 形式の証券コードを EDINET 5 桁コードへ変換して返します.

    引数:
        sec_code: 変換対象の証券コード文字列

    返却値:
        EDINET の5桁コード文字列
    """
    return _converter.to_edinet(sec_code)


def from_edinet_code(edinet_code: str) -> str:
    """EDINET の5桁コードを `stock_master` 形式に戻して返します.

    末尾のゼロを削除して短い形式に戻します。例: '13010' -> '1301'.

    引数:
        edinet_code: EDINET の5桁コード文字列

    返却値:
        元の `stock_master` 形式の証券コード文字列
    """
    return _converter.from_edinet(edinet_code)


__all__ = ["StockCodeConverter", "to_edinet_code", "from_edinet_code"]
