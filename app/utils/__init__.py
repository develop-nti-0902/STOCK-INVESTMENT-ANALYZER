"""`app.utils` パッケージの最小限の初期化モジュール。

このファイルは副作用を起こさないように空に近い状態にしています。
副作用を伴うロガー初期化や DB ヘルパーの import は行わないでください。
必要なユーティリティは `app.utils.logger` や `app.utils.database` を直接 import してください。
"""

__all__: list[str] = []
