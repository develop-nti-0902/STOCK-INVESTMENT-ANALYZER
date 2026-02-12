"""parsed_xbrl の互換差異を吸収する小さなアダプタヘルパー.

様々な parsed_xbrl 実装が `get_data_by_context_ref` のシグネチャを異なる形で
提供しているため、それらを平滑化して扱いやすくします.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)


def get_data(parsed_xbrl: Any, tag: Optional[str] = None, ctx: Optional[str] = None) -> Any:
    """parsed_xbrl の get_data_by_context_ref 呼び出し差異を吸収するヘルパー.

    代表的なシグネチャの違いを安全に試行し、見つかった結果を返します.
    """
    # Defensive: many implementations may raise TypeError for unexpected arg counts
    try:
        if tag is not None and ctx is not None:
            try:
                return parsed_xbrl.get_data_by_context_ref(tag, ctx)
            except TypeError:
                # try one-arg fallback below
                pass

        if ctx is not None:
            try:
                return parsed_xbrl.get_data_by_context_ref(ctx)
            except TypeError:
                pass

        if tag is not None:
            try:
                return parsed_xbrl.get_data_by_context_ref(tag)
            except TypeError:
                pass
    except Exception as exc:
        logger.exception("parsed_xbrl adapter unexpected error: %s", exc)

    # Last-ditch attempts: try common getter names
    for name in ("get", "get_item", "get_value"):
        getter = getattr(parsed_xbrl, name, None)
        if callable(getter):
            try:
                if tag is not None:
                    return getter(tag)
                if ctx is not None:
                    return getter(ctx)
            except Exception:
                continue

    return None


def extract_first_numeric(
    parsed_xbrl: Any, tags: Iterable[str], contexts: Iterable[str]
) -> Optional[float]:
    """指定候補タグ・コンテキストを順に試し、最初に得られる数値を返す."""
    for ctx in contexts:
        for tag in tags:
            val = get_data(parsed_xbrl, tag=tag, ctx=ctx)
            if val is None:
                continue
            try:
                return float(val)
            except (TypeError, ValueError):
                # maybe val is dict-like or list; attempt coarse extraction
                if isinstance(val, (list, tuple)) and val:
                    try:
                        return float(val[0])
                    except Exception:
                        continue
                if isinstance(val, dict):
                    # try values
                    for v in val.values():
                        try:
                            return float(v)
                        except Exception:
                            continue
    return None
