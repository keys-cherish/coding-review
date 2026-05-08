"""重复检测引擎单元测试。"""
from __future__ import annotations

from pathlib import Path

from backend.engines.duplication import (
    DuplicationDetector,
    calc_duplication_rate,
    normalize_tokens,
)
from backend.engines.duplication.rolling_hash import RabinKarpHasher
from backend.engines.parser import parse_file


class TestNormalizer:

    def test_normalizes_identifiers(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "clean.py")
        normalized = normalize_tokens(parsed)
        assert len(normalized) > 0

    def test_normalize_is_deterministic(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "clean.py")
        a = normalize_tokens(parsed)
        b = normalize_tokens(parsed)
        assert [t.norm_value for t in a] == [t.norm_value for t in b]
        assert [t.line for t in a] == [t.line for t in b]


class TestRabinKarp:

    def test_window_hashing_consistency(self) -> None:
        hasher = RabinKarpHasher(window=4)
        tokens = ["a", "b", "c", "d", "e", "f"]
        slices = list(hasher.slide(tokens))
        # 6 个 token，window 4，应当产生 3 个滑窗
        assert len(slices) == 3
        for s in slices:
            assert s.end_index - s.start_index == 4

    def test_short_input_returns_empty(self) -> None:
        hasher = RabinKarpHasher(window=10)
        assert hasher.slide(["a", "b", "c"]) == []

    def test_identical_streams_same_hash(self) -> None:
        hasher = RabinKarpHasher(window=3)
        s1 = list(hasher.slide(["x", "y", "z", "w"]))
        s2 = list(hasher.slide(["x", "y", "z", "w"]))
        assert [a.hash for a in s1] == [b.hash for b in s2]


class TestDetector:

    def test_detects_pasted_block(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "messy.py")
        detector = DuplicationDetector(window=15, min_lines=3)
        blocks = detector.detect([parsed])
        # 文件里 duplicate_block_a / b 应该形成至少一个重复块
        assert any(b.line_length >= 3 and len(b.occurrences) >= 2 for b in blocks)

    def test_clean_file_no_duplicates(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "clean.py")
        detector = DuplicationDetector(window=20, min_lines=5)
        blocks = detector.detect([parsed])
        # clean.py 太小且没有重复
        token_blocks = [b for b in blocks if b.detection_method == "token"]
        assert all(b.line_length < 5 for b in token_blocks)

    def test_calc_duplication_rate_bounds(self) -> None:
        # 边界：0 总行数应安全返回 0
        rate = calc_duplication_rate([], total_loc=0)
        assert 0.0 <= rate <= 1.0
