"""
Rabin-Karp 滚动哈希实现。

用于高效计算 token 序列上长度固定的滑窗哈希，时间复杂度 O(n)。
公式：
    H(0)   = sum(s[i] * base^(L-1-i))  for i in [0, L)
    H(k+1) = (H(k) - s[k]*base^(L-1)) * base + s[k+L]    (mod P)

参考：Karp & Rabin (1987) 字符串匹配算法。
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings


@dataclass
class HashSlice:
    """滑窗内一段 token 的哈希结果。"""
    hash: int
    start_index: int  # 在 token 序列中的起始下标
    end_index: int    # 终止下标（不含）


class RabinKarpHasher:
    """对 token 字符串序列做 Rabin-Karp 滑窗哈希。"""

    def __init__(self, window: int | None = None,
                 base: int | None = None, mod: int | None = None) -> None:
        self.window = window or settings.dup_window_size
        self.base = base or settings.dup_hash_base
        self.mod = mod or settings.dup_hash_mod

    @staticmethod
    def _value(token: str) -> int:
        """将 token 字符串映射为整数（字符序列累加哈希）。"""
        v = 0
        for ch in token:
            v = (v * 131 + ord(ch)) & 0x7FFFFFFF
        return v

    def slide(self, tokens: list[str]) -> list[HashSlice]:
        """返回所有滑窗哈希。"""
        n = len(tokens)
        L = self.window
        if n < L:
            return []

        values = [self._value(t) for t in tokens]
        base, mod = self.base, self.mod

        # base^(L-1) mod
        high = pow(base, L - 1, mod)

        # 初始窗口 hash
        h = 0
        for i in range(L):
            h = (h * base + values[i]) % mod
        out: list[HashSlice] = [HashSlice(hash=h, start_index=0, end_index=L)]

        # 滑动
        for i in range(1, n - L + 1):
            h = ((h - values[i - 1] * high) * base + values[i + L - 1]) % mod
            if h < 0:
                h += mod
            out.append(HashSlice(hash=h, start_index=i, end_index=i + L))
        return out
