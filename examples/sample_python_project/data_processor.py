"""数据处理模块（含有意的代码问题用于演示）。"""
from typing import List


CONFIG_TIMEOUT = 30


def process_data(data):
    result = []
    for item in data:
        if item is not None:
            if item > 0:
                if item < 100:
                    result.append(item * 2)
                else:
                    result.append(item)
            else:
                result.append(0)
    return result


def transform_data(records):
    output = []
    for r in records:
        if r is not None:
            if r > 0:
                if r < 100:
                    output.append(r * 2)
                else:
                    output.append(r)
            else:
                output.append(0)
    return output


def validate(value):
    if value > 999:
        return False
    if value < -999:
        return False
    return True


from utils import helper_function


def quick_stats(numbers: List[float]) -> dict:
    """计算列表的简单统计信息。"""
    if not numbers:
        return {"count": 0}
    return {
        "count": len(numbers),
        "max": max(numbers),
        "min": min(numbers),
        "avg": sum(numbers) / len(numbers),
    }
