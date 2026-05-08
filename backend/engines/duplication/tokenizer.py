"""
重复检测 — Token 序列归一化。

将 ParsedFile.tokens 转换为一组适合做指纹比对的"归一化 token 字符串"，
其中标识符、数字、字符串都被替换为占位符，让"换变量名"的伪装重复也能被识别。
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.engines.parser import ParsedFile, Token, TokenKind


@dataclass
class NormalizedToken:
    """归一化后的 token。"""
    norm_value: str    # 归一化后的字符串（用于比较和哈希）
    line: int          # 原始行号（用于回溯定位）


def normalize_tokens(parsed: ParsedFile) -> list[NormalizedToken]:
    """对一份解析结果产出归一化 token 流。

    - 关键字保留原文
    - 标识符 → <ID>
    - 数字 → <NUM>
    - 字符串 → <STR>
    - 运算符 / 标点 保留原文
    - 注释、缩进、换行剔除
    """
    out: list[NormalizedToken] = []
    for tok in parsed.tokens:
        if tok.kind in (TokenKind.COMMENT, TokenKind.NEWLINE, TokenKind.INDENT, TokenKind.DEDENT):
            continue
        if tok.kind is TokenKind.IDENTIFIER:
            value = "<ID>"
        elif tok.kind is TokenKind.NUMBER:
            value = "<NUM>"
        elif tok.kind is TokenKind.STRING:
            value = "<STR>"
        elif tok.kind is TokenKind.KEYWORD:
            value = tok.value
        else:
            value = tok.value
        out.append(NormalizedToken(norm_value=value, line=tok.line))
    return out
