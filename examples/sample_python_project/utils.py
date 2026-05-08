"""一个写得相对规范的工具模块，作为对照。"""
from __future__ import annotations

from typing import Iterable


MAX_RETRY = 3
DEFAULT_TIMEOUT = 30


def helper_function(value: int) -> int:
    """对输入值做一个简单变换。

    Args:
        value: 整数输入。

    Returns:
        变换后的整数。
    """
    return value * 2 + 1


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，避免除零异常。"""
    if denominator == 0:
        return default
    return numerator / denominator


def chunk_list(items: Iterable, size: int) -> list[list]:
    """将可迭代对象按固定大小切块。"""
    chunk: list = []
    out: list[list] = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            out.append(chunk)
            chunk = []
    if chunk:
        out.append(chunk)
    return out
