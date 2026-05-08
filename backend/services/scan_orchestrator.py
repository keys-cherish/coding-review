"""
扫描编排器（ScanOrchestrator）。

职责：
1. 加载某个 Version 下所有源文件
2. 调度 RuleEngine / ComplexityAnalyzer / DuplicationDetector 协同工作
3. 实时推送 WebSocket 进度
4. 汇总评分、入库、生成报告
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.engines.complexity import ComplexityAnalyzer, FunctionComplexity
from backend.engines.duplication import DuplicationDetector, calc_duplication_rate
from backend.engines.parser import ParsedFile, get_parser
from backend.engines.rules import Issue as EngineIssue, RuleEngine
from backend.engines.scoring import compute_overall
from backend.models import (
    ComplexityMetric,
    Duplication,
    Issue,
    ScanTask,
    ScanTaskStatus,
    SourceFile,
    Version,
)
from backend.services.upload_service import collect_source_files, hash_file
from backend.services.ws_manager import manager
from backend.utils import logger


class ScanOrchestrator:
    """扫描编排器（无状态，每次 scan 一个独立任务）。"""

    def __init__(
        self,
        rule_engine: RuleEngine | None = None,
        complexity_analyzer: ComplexityAnalyzer | None = None,
        dup_detector: DuplicationDetector | None = None,
    ) -> None:
        self.rule_engine = rule_engine or RuleEngine()
        self.complexity_analyzer = complexity_analyzer or ComplexityAnalyzer()
        self.dup_detector = dup_detector or DuplicationDetector()

    async def run_scan(self, scan_id: int, db: AsyncSession) -> None:
        """主入口：执行一次完整扫描。"""
        task = await db.get(ScanTask, scan_id)
        if task is None:
            logger.error(f"ScanTask {scan_id} 不存在")
            return

        version = await db.get(Version, task.version_id)
        if version is None:
            await self._fail(db, task, "关联 Version 不存在")
            return

        # 主动加载 project，避免后续 lazy load 在子线程或非 await 上下文中触发
        from backend.models import Project as _Project
        project = await db.get(_Project, version.project_id)
        project_language = project.language if project else "multi"

        try:
            await self._mark_running(db, task)
            await self._broadcast(scan_id, task)

            root = Path(version.upload_path)
            if not root.exists():
                raise FileNotFoundError(f"上传目录不存在: {root}")

            # 1. 收集源文件
            entries = collect_source_files(root, project_language)
            if not entries:
                raise ValueError("未发现可分析的源文件")

            await self._broadcast(scan_id, task, message=f"发现 {len(entries)} 个源文件")

            # 2. 在主线程内顺序处理（CPU 密集部分用 to_thread 异步化），
            #    但所有 DB 操作都在协程主线程完成，避免 greenlet 错误
            sf_records: list[SourceFile] = []
            parsed_list: list[ParsedFile] = []
            issues_per_file: dict[int, list[EngineIssue]] = {}
            metrics_per_file: dict[int, list[FunctionComplexity]] = {}

            total_loc = 0
            total = len(entries)

            for idx, entry in enumerate(entries):
                abs_path, rel_path, file_lang, line_count, size = entry
                # CPU 部分进 thread
                parsed, issues, metrics, loc = await asyncio.to_thread(
                    self._analyze_one_file, abs_path, file_lang
                )
                # DB 部分回主协程
                sf = SourceFile(
                    version_id=version.id,
                    relative_path=rel_path,
                    language=file_lang,
                    lines_of_code=loc,
                    total_lines=line_count,
                    file_hash=hash_file(abs_path),
                )
                db.add(sf)
                await db.flush()
                sf_records.append(sf)
                parsed_list.append(parsed)
                issues_per_file[sf.id] = issues
                metrics_per_file[sf.id] = metrics
                total_loc += loc

                task.progress = (idx + 1) / max(total, 1) * 0.85  # 留 15% 给重复+评分
                task.current_file = rel_path
                await db.flush()
                await self._broadcast(scan_id, task, message=f"分析: {rel_path}")

            # 3. 写入 Issue 与 ComplexityMetric
            issues_count = {"error": 0, "warning": 0, "info": 0}
            max_cc = 0
            cc_total = 0
            cc_func_count = 0
            all_engine_issues: list[EngineIssue] = []
            all_metrics: list[FunctionComplexity] = []

            for sf in sf_records:
                for ei in issues_per_file[sf.id]:
                    db.add(Issue(
                        scan_task_id=task.id,
                        source_file_id=sf.id,
                        rule_code=ei.rule_code,
                        category=ei.category,
                        severity=ei.severity,
                        line=ei.line,
                        column=ei.column,
                        end_line=ei.end_line,
                        message=ei.message,
                        code_snippet=ei.code_snippet,
                        suggestion=ei.suggestion,
                    ))
                    issues_count[ei.severity] = issues_count.get(ei.severity, 0) + 1
                    all_engine_issues.append(ei)

                # 文件健康度（先按 issue 算）
                file_score = max(0.0, 100.0 - len(issues_per_file[sf.id]) * 3)
                sf.health_score = file_score

                for m in metrics_per_file[sf.id]:
                    db.add(ComplexityMetric(
                        source_file_id=sf.id,
                        function_name=m.function_name,
                        start_line=m.start_line,
                        end_line=m.end_line,
                        lines=m.lines,
                        cyclomatic=m.cyclomatic,
                        cognitive=m.cognitive,
                        nesting_depth=m.nesting_depth,
                        parameters=m.parameters,
                        risk_level=m.risk_level,
                    ))
                    max_cc = max(max_cc, m.cyclomatic)
                    cc_total += m.cyclomatic
                    cc_func_count += 1
                    all_metrics.append(m)

            # 4. 重复检测
            await self._broadcast(scan_id, task, message="正在做跨文件重复检测...")
            blocks = await asyncio.to_thread(self.dup_detector.detect, parsed_list)
            for b in blocks:
                db.add(Duplication(
                    scan_task_id=task.id,
                    fingerprint=b.fingerprint,
                    token_length=b.token_length,
                    line_length=b.line_length,
                    occurrences=len(b.occurrences),
                    detection_method=b.detection_method,
                    occurrences_json=DuplicationDetector.serialize_occurrences(b),
                ))
            duplication_rate = calc_duplication_rate(blocks, total_loc)

            # 5. 评分
            score = compute_overall(all_engine_issues, duplication_rate, all_metrics, total_loc)

            # 6. 写回 ScanTask 汇总字段
            task.total_issues = sum(issues_count.values())
            task.error_count = issues_count.get("error", 0)
            task.warning_count = issues_count.get("warning", 0)
            task.info_count = issues_count.get("info", 0)
            task.duplication_rate = duplication_rate
            task.avg_complexity = round(cc_total / cc_func_count, 2) if cc_func_count else 0
            task.max_complexity = max_cc
            task.spec_score = score.spec_score
            task.dup_score = score.dup_score
            task.complexity_score = score.complexity_score
            task.overall_score = score.overall_score
            task.grade = score.grade

            task.progress = 1.0
            task.status = ScanTaskStatus.DONE
            task.finished_at = datetime.utcnow()

            # 同步 Version 统计
            version.total_files = len(sf_records)
            version.total_lines = total_loc

            await db.flush()
            await self._broadcast(scan_id, task, message="完成")

        except Exception as e:
            logger.exception(f"扫描 {scan_id} 失败: {e}")
            await self._fail(db, task, f"{type(e).__name__}: {e}")
            return

    # ---------- 内部 ----------

    @staticmethod
    def _infer_language(version: Version) -> str:
        # 取项目语言，但 collect_source_files 会按扩展名再过滤
        return getattr(version.project, "language", None) or "multi"

    def _analyze_one_file(
        self,
        path: Path,
        language: str,
    ) -> tuple[ParsedFile, list[EngineIssue], list[FunctionComplexity], int]:
        """同步函数：解析 + 规则 + 复杂度。"""
        try:
            parser = get_parser(language)
            parsed = parser.parse(path)
            if parsed.parse_error:
                logger.warning(f"{path} 解析存在问题: {parsed.parse_error}")
            issues = self.rule_engine.check_file(parsed)
            metrics = self.complexity_analyzer.analyze(parsed)
            return parsed, issues, metrics, parsed.lines_of_code
        except Exception as e:
            logger.warning(f"分析 {path} 失败: {type(e).__name__}: {e}")
            empty = ParsedFile(
                file_path=path,
                language=language,
                raw_text="",
                raw_lines=[],
                tokens=[],
                functions=[],
                classes=[],
                imports=[],
                ast_root=None,
                parse_error=str(e),
            )
            return empty, [], [], 0

    @staticmethod
    async def _mark_running(db: AsyncSession, task: ScanTask) -> None:
        task.status = ScanTaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.progress = 0.0
        await db.flush()

    @staticmethod
    async def _fail(db: AsyncSession, task: ScanTask, msg: str) -> None:
        task.status = ScanTaskStatus.FAILED
        task.error_msg = msg
        task.finished_at = datetime.utcnow()
        await db.flush()
        await manager.broadcast(task.id, {
            "scan_id": task.id,
            "status": "failed",
            "progress": task.progress,
            "message": msg,
        })

    @staticmethod
    async def _broadcast(scan_id: int, task: ScanTask, message: str | None = None) -> None:
        await manager.broadcast(scan_id, {
            "scan_id": scan_id,
            "status": task.status,
            "progress": task.progress,
            "current_file": task.current_file,
            "issues_found": task.total_issues,
            "message": message,
        })
