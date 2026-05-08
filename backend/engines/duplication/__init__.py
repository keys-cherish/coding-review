"""
重复检测引擎导出。
"""
from backend.engines.duplication.detector import (
    DuplicationBlock,
    DuplicationDetector,
    Occurrence,
    calc_duplication_rate,
)
from backend.engines.duplication.rolling_hash import HashSlice, RabinKarpHasher
from backend.engines.duplication.tokenizer import NormalizedToken, normalize_tokens

__all__ = [
    "DuplicationBlock",
    "DuplicationDetector",
    "HashSlice",
    "NormalizedToken",
    "Occurrence",
    "RabinKarpHasher",
    "calc_duplication_rate",
    "normalize_tokens",
]
