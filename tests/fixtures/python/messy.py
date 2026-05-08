"""规范测试 fixture：包含命名错误、缩进、魔法值、长行、无效代码、复杂度过高。

故意写得"代码味"很重，用来覆盖大多数规则。
"""
import os, sys


def BadFunctionName(x,y):
    if x>0:
        if y>0:
            if x>y:
                if x-y>100:
                    return 9999
    return 0


GLOBAL_VAR_should_be_upper = 42


class lower_case_class:

    def DoSomething(self,
                    a, b, c, d, e, f, g):
        if a > 100:
            print("found too many")
        if b > 100:
            print("found too many")
        if c > 100:
            print("found too many")
        unused_local = 12345
        return a + b + c


def unused_function():
    pass


# 一行非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长非常长 line
TOO_LONG = "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghij"


def duplicate_block_a():
    items = []
    for i in range(10):
        if i % 2 == 0:
            items.append(i * 3)
        else:
            items.append(i * 5)
    return items


def duplicate_block_b():
    items = []
    for i in range(10):
        if i % 2 == 0:
            items.append(i * 3)
        else:
            items.append(i * 5)
    return items


def super_complex(a, b, c, d, e, f, g):
    """故意写成高圈复杂度，覆盖 medium / high 风险级。"""
    result = 0
    if a > 0:
        result += 1
    if b > 0:
        result += 1
    if c > 0:
        result += 1
    if d > 0:
        result += 1
    if e > 0:
        result += 1
    if f > 0:
        result += 1
    if g > 0:
        result += 1
    for i in range(10):
        if i % 2 == 0:
            result += i
        elif i % 3 == 0:
            result -= i
    while result > 100 and result < 200:
        result -= 1
    return result
