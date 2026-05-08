"""命名规范、注释、复杂度都达标的清洁文件。"""


def add(a: int, b: int) -> int:
    """两个整数求和。"""
    return a + b


def is_even(value: int) -> bool:
    """判断是否偶数。"""
    return value % 2 == 0


class Calculator:
    """简易计算器。"""

    def __init__(self, base: int = 0) -> None:
        self.base = base

    def add(self, x: int) -> int:
        return self.base + x
