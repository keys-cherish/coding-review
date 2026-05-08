"""
重复检测主入口。

双引擎设计：
1. Token 级（Rabin-Karp）：细粒度，能识别局部代码块复制粘贴
2. AST 级（节点归一化指纹）：函数级，能识别"换皮重复"

输出：DuplicationBlock 列表，每个块包含至少 2 处出现。
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from backend.config import settings
from backend.engines.duplication.ast_normalizer import fingerprint_all_functions
from backend.engines.duplication.rolling_hash import RabinKarpHasher
from backend.engines.duplication.tokenizer import normalize_tokens
from backend.engines.parser import ParsedFile


@dataclass
class Occurrence:
    """重复块在某文件中的一次出现。"""
    file_path: str
    start_line: int
    end_line: int


@dataclass
class DuplicationBlock:
    """一组互为重复的代码块。"""
    fingerprint: str          # 指纹（hash 十六进制）
    token_length: int         # 重复 token 数量（token 引擎）；AST 引擎为 0
    line_length: int          # 平均跨越行数
    occurrences: list[Occurrence] = field(default_factory=list)
    detection_method: str = "token"  # token / ast


class DuplicationDetector:
    """对一组 ParsedFile 做跨文件的重复检测。"""

    def __init__(
        self,
        window: int | None = None,
        min_lines: int | None = None,
    ) -> None:
        self.window = window or settings.dup_window_size
        self.min_lines = min_lines or settings.dup_min_lines
        self.hasher = RabinKarpHasher(window=self.window)

    # ============ Token 引擎 ============

    def _token_engine(self, files: list[ParsedFile]) -> list[DuplicationBlock]:
        """跨文件用 Rabin-Karp 找出哈希相同的 token 窗口。"""
        # bucket: hash -> [(file_index, slice)]
        bucket: dict[int, list[tuple[int, int, int, int]]] = defaultdict(list)

        per_file_tokens: list[list] = []
        per_file_strs: list[list[str]] = []
        for fi, parsed in enumerate(files):
            ntokens = normalize_tokens(parsed)
            per_file_tokens.append(ntokens)
            strs = [t.norm_value for t in ntokens]
            per_file_strs.append(strs)
            slices = self.hasher.slide(strs)
            for sl in slices:
                start_line = ntokens[sl.start_index].line if sl.start_index < len(ntokens) else 0
                end_line = ntokens[sl.end_index - 1].line if sl.end_index - 1 < len(ntokens) else start_line
                bucket[sl.hash].append((fi, sl.start_index, start_line, end_line))

        blocks: list[DuplicationBlock] = []
        seen_pairs: set[tuple[int, int, int, int]] = set()
        for h, occs in bucket.items():
            if len(occs) < 2:
                continue
            # 二次精确比对（防哈希碰撞）
            verified_groups: dict[tuple[str, ...], list[tuple[int, int, int, int]]] = defaultdict(list)
            for occ in occs:
                fi, start, sl, el = occ
                key = tuple(per_file_strs[fi][start:start + self.window])
                verified_groups[key].append(occ)

            for key, group in verified_groups.items():
                if len(group) < 2:
                    continue
                # 行跨度过短跳过
                line_spans = [el - sl + 1 for (_, _, sl, el) in group]
                avg_lines = sum(line_spans) / len(line_spans)
                if avg_lines < self.min_lines:
                    continue
                # 同文件相同位置去重
                dedup_key = tuple(sorted((fi, sl) for (fi, _, sl, _) in group))
                if dedup_key in seen_pairs:
                    continue
                seen_pairs.add(dedup_key)
                block = DuplicationBlock(
                    fingerprint=hex(h)[2:].zfill(16),
                    token_length=self.window,
                    line_length=int(avg_lines),
                    occurrences=[
                        Occurrence(
                            file_path=str(files[fi].file_path),
                            start_line=sl,
                            end_line=el,
                        )
                        for (fi, _, sl, el) in group
                    ],
                    detection_method="token",
                )
                blocks.append(block)
        return blocks

    # ============ AST 引擎 ============

    def _ast_engine(self, files: list[ParsedFile]) -> list[DuplicationBlock]:
        """跨文件函数级 AST 指纹比对。"""
        bucket: dict[str, list[tuple[ParsedFile, str, int, int]]] = defaultdict(list)
        for parsed in files:
            fps = fingerprint_all_functions(parsed)
            qn_to_func = {f.qualified_name: f for f in parsed.functions}
            for qn, fp in fps.items():
                f = qn_to_func.get(qn)
                if f is None:
                    continue
                bucket[fp].append((parsed, qn, f.start_line, f.end_line))

        blocks: list[DuplicationBlock] = []
        for fp, occs in bucket.items():
            if len(occs) < 2:
                continue
            line_spans = [el - sl + 1 for (_, _, sl, el) in occs]
            avg_lines = sum(line_spans) / len(line_spans)
            if avg_lines < self.min_lines:
                continue
            block = DuplicationBlock(
                fingerprint=fp[:16],
                token_length=0,
                line_length=int(avg_lines),
                occurrences=[
                    Occurrence(
                        file_path=str(parsed.file_path),
                        start_line=sl,
                        end_line=el,
                    )
                    for (parsed, _, sl, el) in occs
                ],
                detection_method="ast",
            )
            blocks.append(block)
        return blocks

    # ============ 主入口 ============

    def detect(self, files: list[ParsedFile]) -> list[DuplicationBlock]:
        """运行双引擎，合并去重后返回。"""
        token_blocks = self._token_engine(files)
        ast_blocks = self._ast_engine(files)

        # AST 检出的函数级重复优先（信号更强），与 token 检出有重叠时去掉 token 的
        ast_ranges: set[tuple[str, int, int]] = set()
        for b in ast_blocks:
            for occ in b.occurrences:
                ast_ranges.add((occ.file_path, occ.start_line, occ.end_line))

        merged: list[DuplicationBlock] = list(ast_blocks)
        for b in token_blocks:
            covered = False
            for occ in b.occurrences:
                for (fp, sl, el) in ast_ranges:
                    if occ.file_path == fp and occ.start_line >= sl and occ.end_line <= el:
                        covered = True
                        break
                if covered:
                    break
            if not covered:
                merged.append(b)
        return merged

    @staticmethod
    def serialize_occurrences(block: DuplicationBlock) -> str:
        """把 occurrences 序列化为 JSON 字符串（用于入库）。"""
        return json.dumps([asdict(o) for o in block.occurrences], ensure_ascii=False)


def calc_duplication_rate(
    blocks: list[DuplicationBlock],
    total_loc: int,
) -> float:
    """计算重复率：(重复块行数总和 - 每组保留 1 份的行数) / 总有效代码行数。"""
    if total_loc <= 0:
        return 0.0
    dup_lines = 0
    for b in blocks:
        # 一组 N 处出现，重复"贡献"是 (N-1) * 平均行数
        if len(b.occurrences) <= 1:
            continue
        per = b.line_length or sum(o.end_line - o.start_line + 1 for o in b.occurrences) / len(b.occurrences)
        dup_lines += int(per * (len(b.occurrences) - 1))
    return min(1.0, dup_lines / total_loc)
