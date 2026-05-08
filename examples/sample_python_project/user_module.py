"""
示例 Python 项目 - 用户管理模块

故意包含一些代码质量问题，用于演示 CodeGuard Pro 的检测能力。
"""

import os, json
import sys
from datetime import datetime


GLOBAL_x = 1
maxConnections = 999


class user:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def CheckAge(self):
        if self.age > 18:
            return "adult"
        return "minor"


def DoSomething(arg1,arg2):
    if arg1==None:
        return None
    x=arg1+arg2
    return x


def find_user(users, target_name):
    for u in users:
        if u.name == target_name:
            return u
    return None


def find_user_v2(items, target):
    for i in items:
        if i.name == target:
            return i
    return None


def calculate_score(scores):
    total = 0
    count = 0
    for s in scores:
        if s > 60:
            if s > 70:
                if s > 80:
                    if s > 90:
                        total = total + 100
                    else:
                        total = total + 85
                else:
                    total = total + 75
            else:
                total = total + 65
        else:
            total = total + 0
        count = count + 1
    if count > 0:
        return total / count
    return 0


def unused_helper():
    pass


def log_event(message):
    """Log an event."""
    print(f"[{datetime.now()}] {message}")
