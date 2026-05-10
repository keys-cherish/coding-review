"""文件相关工具函数。"""
from __future__ import annotations

import hashlib
import os
import zipfile
from pathlib import Path
from typing import Iterator


def sha256_of_file(path: Path) -> str:
    """计算文件 SHA-256 摘要。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """安全解压 ZIP，防止 zip-slip 攻击。"""
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_path = (dest_dir / member.filename).resolve()
            if not str(member_path).startswith(str(dest_dir)):
                raise ValueError(f"非法路径: {member.filename}")
            if member.is_dir():
                member_path.mkdir(parents=True, exist_ok=True)
            else:
                member_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(member_path, "wb") as dst:
                    dst.write(src.read())


# 默认排除的目录
DEFAULT_IGNORE_DIRS = {
    "__pycache__", ".git", ".svn", ".idea", ".vscode", "node_modules",
    "venv", ".venv", "env", "dist", "build", "target", ".pytest_cache",
    "htmlcov", ".tox", ".mypy_cache", ".ruff_cache",
}


def walk_source_files(
    root: Path,
    extensions: tuple[str, ...],
    ignore_dirs: set[str] | None = None,
) -> Iterator[Path]:
    """递归遍历给定后缀的源文件，跳过常见非源码目录。"""
    ignore = ignore_dirs or DEFAULT_IGNORE_DIRS
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignore and not d.startswith(".")]
        for fname in files:
            if any(fname.endswith(ext) for ext in extensions):
                yield Path(current_root) / fname


def detect_language(filename: str) -> str | None:
    """根据扩展名识别语言。"""
    lower = filename.lower()
    if lower.endswith(".py"):
        return "python"
    if lower.endswith(".java"):
        return "java"
    if lower in {".env", "dockerfile"} or lower.endswith((
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".env",
    )):
        return "config"
    return None


def read_text_safely(path: Path) -> str:
    """安全读取文本文件，自动尝试编码。"""
    for encoding in ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")
