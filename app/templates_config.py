"""テンプレートエンジンの設定モジュール.

循環インポートを避けるため、Jinja2Templatesのインスタンスを
このモジュールで管理します。
"""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
