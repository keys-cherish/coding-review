"""
CodeGuard Pro 全局配置模块

集中管理项目运行时配置，支持环境变量覆盖。
所有路径相对于项目根目录，便于在不同部署位置工作。
"""
from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """运行时配置，可通过 .env 或环境变量覆盖。"""

    model_config = SettingsConfigDict(
        env_prefix="CODEGUARD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CodeGuard Pro"
    app_version: str = "1.0.0"
    app_description: str = "智能代码质量管理与规范检测平台"
    debug: bool = False

    db_path: Path = Field(default=PROJECT_ROOT / "data" / "codeguard.db")
    db_echo: bool = False

    upload_dir: Path = Field(default=PROJECT_ROOT / "data" / "uploads")
    report_dir: Path = Field(default=PROJECT_ROOT / "data" / "reports")
    scan_cache_dir: Path = Field(default=PROJECT_ROOT / "data" / "scan_cache")
    max_upload_size_mb: int = 100

    frontend_dir: Path = Field(default=PROJECT_ROOT / "frontend")

    scan_concurrency: int = 4
    scan_max_files: int = 5000
    scan_max_file_size_kb: int = 1024

    dup_window_size: int = 50
    dup_min_lines: int = 6
    dup_hash_base: int = 257
    dup_hash_mod: int = 1_000_000_007

    complexity_warn_threshold: int = 10
    complexity_critical_threshold: int = 20

    score_weight_spec: float = 0.45
    score_weight_dup: float = 0.30
    score_weight_complexity: float = 0.25

    host: str = "127.0.0.1"
    port: int = 8000

    supported_languages: tuple[str, ...] = ("python", "java", "config")
    python_extensions: tuple[str, ...] = (".py",)
    java_extensions: tuple[str, ...] = (".java",)
    config_extensions: tuple[str, ...] = (
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".env",
    )

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.scan_cache_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
