"""
上传服务：处理 ZIP 上传与项目目录解析。
"""
from __future__ import annotations

import shutil
from pathlib import Path

from backend.config import settings
from backend.utils.file_utils import (
    detect_language,
    safe_extract_zip,
    sha256_of_file,
    walk_source_files,
)


def save_upload(
    project_id: int,
    version_id: int,
    src_zip: Path,
    delete_src: bool = True,
) -> Path:
    """把上传的 ZIP 解压到 data/uploads/<project_id>/<version_id>/，返回解压目录。"""
    dest_root = settings.upload_dir / str(project_id) / str(version_id)
    if dest_root.exists():
        shutil.rmtree(dest_root)
    dest_root.mkdir(parents=True, exist_ok=True)
    safe_extract_zip(src_zip, dest_root)
    if delete_src:
        src_zip.unlink(missing_ok=True)

    # 智能展开：如果 ZIP 解压后只有一个根目录，向上提一层
    children = list(dest_root.iterdir())
    if len(children) == 1 and children[0].is_dir():
        only = children[0]
        # 把内容上移
        tmp = dest_root.with_suffix(".__tmp__")
        only.rename(tmp)
        shutil.rmtree(dest_root)
        tmp.rename(dest_root)
    return dest_root


def collect_source_files(
    root: Path,
    language: str,
) -> list[tuple[Path, str, str, int, int]]:
    """遍历源码目录，返回 [(abs_path, relative_path, language, total_lines, file_size)]。

    若 language 为 'multi'，则同时收集 Python 和 Java 文件。
    """
    if language == "python":
        exts = settings.python_extensions
    elif language == "java":
        exts = settings.java_extensions
    else:
        exts = settings.python_extensions + settings.java_extensions

    out: list[tuple[Path, str, str, int, int]] = []
    for p in walk_source_files(root, exts):
        try:
            size = p.stat().st_size
            if size > settings.scan_max_file_size_kb * 1024:
                continue
            with open(p, "rb") as f:
                line_count = sum(1 for _ in f)
            file_lang = detect_language(p.name) or "unknown"
            rel = p.relative_to(root).as_posix()
            out.append((p, rel, file_lang, line_count, size))
            if len(out) >= settings.scan_max_files:
                break
        except OSError:
            continue
    return out


def hash_file(path: Path) -> str:
    return sha256_of_file(path)
