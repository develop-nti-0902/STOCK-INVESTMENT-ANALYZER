"""
Repository層パッケージ

データアクセス層の実装を提供する。
Repository Patternを採用し、データベース操作の抽象化を行う。
"""

from app.repositories.base import BaseRepository

__all__ = ["BaseRepository"]
