// Package store 管理 archd 对 SQLite 的读写。
//
// 设计要点
// --------
// 1. 与 Python 端共用同一个 codeguard.db，零迁移成本。
// 2. archd 自建的图结构表统一以 arch_ 前缀命名，避免与 Python 表冲突。
// 3. 全部建表语句使用 IF NOT EXISTS，允许 Python 先跑、Go 后跑，或反之。
// 4. sqlx 提供 Get/Select 的结构体映射，SQL 明写在常量里，便于审计。
package store

import (
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
	_ "github.com/mattn/go-sqlite3"
)

// Open 打开 SQLite 连接；启用 foreign keys、WAL 以获得并发读性能。
func Open(path string) (*sqlx.DB, error) {
	dsn := fmt.Sprintf("file:%s?_journal_mode=WAL&_foreign_keys=on&_busy_timeout=5000", path)
	db, err := sqlx.Open("sqlite3", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1) // SQLite 写单连接更稳
	db.SetMaxIdleConns(1)
	db.SetConnMaxLifetime(time.Hour)
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

// Migrate 创建 archd 所需的全部表；幂等。
func Migrate(db *sqlx.DB) error {
	stmts := []string{
		// ── 图结构 ─────────────────────────────────────────────────────
		`CREATE TABLE IF NOT EXISTS arch_modules (
			scan_id      INTEGER NOT NULL,
			module_id    TEXT    NOT NULL,
			file_path    TEXT    NOT NULL,
			language     TEXT    NOT NULL,
			loc          INTEGER NOT NULL DEFAULT 0,
			fan_in       INTEGER NOT NULL DEFAULT 0,
			fan_out      INTEGER NOT NULL DEFAULT 0,
			layer        TEXT    NOT NULL DEFAULT '',
			PRIMARY KEY (scan_id, module_id)
		)`,
		`CREATE TABLE IF NOT EXISTS arch_edges (
			scan_id      INTEGER NOT NULL,
			src          TEXT    NOT NULL,
			dst          TEXT    NOT NULL,
			kind         TEXT    NOT NULL DEFAULT 'import',
			count        INTEGER NOT NULL DEFAULT 1,
			is_wildcard  INTEGER NOT NULL DEFAULT 0,
			PRIMARY KEY (scan_id, src, dst, kind)
		)`,
		`CREATE TABLE IF NOT EXISTS arch_cycles (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			scan_id      INTEGER NOT NULL,
			size         INTEGER NOT NULL,
			severity     TEXT    NOT NULL,
			modules_json TEXT    NOT NULL,
			path_json    TEXT    NOT NULL
		)`,

		// ── 符号 ───────────────────────────────────────────────────────
		`CREATE TABLE IF NOT EXISTS arch_symbols (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			scan_id      INTEGER NOT NULL,
			name         TEXT    NOT NULL,
			kind         TEXT    NOT NULL,
			file_path    TEXT    NOT NULL,
			line         INTEGER NOT NULL DEFAULT 0,
			parent       TEXT    NOT NULL DEFAULT ''
		)`,
		`CREATE INDEX IF NOT EXISTS idx_arch_symbols_scan ON arch_symbols(scan_id, name)`,
		`CREATE TABLE IF NOT EXISTS arch_calls (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			scan_id      INTEGER NOT NULL,
			caller       TEXT    NOT NULL,
			callee       TEXT    NOT NULL,
			file_path    TEXT    NOT NULL,
			line         INTEGER NOT NULL DEFAULT 0
		)`,
		`CREATE INDEX IF NOT EXISTS idx_arch_calls_scan ON arch_calls(scan_id, caller)`,
		`CREATE TABLE IF NOT EXISTS arch_var_refs (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			scan_id      INTEGER NOT NULL,
			var_name     TEXT    NOT NULL,
			action       TEXT    NOT NULL,
			file_path    TEXT    NOT NULL,
			line         INTEGER NOT NULL DEFAULT 0
		)`,

		// ── 高级分析 ───────────────────────────────────────────────────
		`CREATE TABLE IF NOT EXISTS arch_patterns (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			scan_id      INTEGER NOT NULL,
			pattern      TEXT    NOT NULL,
			confidence   REAL    NOT NULL,
			evidence     TEXT    NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS arch_violations (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			scan_id      INTEGER NOT NULL,
			kind         TEXT    NOT NULL,
			src          TEXT    NOT NULL,
			dst          TEXT    NOT NULL DEFAULT '',
			severity     TEXT    NOT NULL,
			detail       TEXT    NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS arch_hotspots (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			scan_id      INTEGER NOT NULL,
			module_id    TEXT    NOT NULL,
			score        REAL    NOT NULL,
			reason       TEXT    NOT NULL
		)`,

		// ── ER 模型 ────────────────────────────────────────────────────
		`CREATE TABLE IF NOT EXISTS er_tables (
			scan_id      INTEGER NOT NULL,
			table_name   TEXT    NOT NULL,
			source_file  TEXT    NOT NULL,
			PRIMARY KEY (scan_id, table_name)
		)`,
		`CREATE TABLE IF NOT EXISTS er_columns (
			scan_id      INTEGER NOT NULL,
			table_name   TEXT    NOT NULL,
			col_name     TEXT    NOT NULL,
			col_type     TEXT    NOT NULL DEFAULT '',
			is_pk        INTEGER NOT NULL DEFAULT 0,
			is_fk        INTEGER NOT NULL DEFAULT 0,
			fk_table     TEXT    NOT NULL DEFAULT '',
			fk_col       TEXT    NOT NULL DEFAULT '',
			PRIMARY KEY (scan_id, table_name, col_name)
		)`,
		`CREATE TABLE IF NOT EXISTS er_relations (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			scan_id      INTEGER NOT NULL,
			from_table   TEXT    NOT NULL,
			to_table     TEXT    NOT NULL,
			kind         TEXT    NOT NULL
		)`,

		// ── 评分 ───────────────────────────────────────────────────────
		`CREATE TABLE IF NOT EXISTS arch_radar (
			scan_id      INTEGER PRIMARY KEY,
			clarity      REAL    NOT NULL DEFAULT 0,
			isolation    REAL    NOT NULL DEFAULT 0,
			decoupling   REAL    NOT NULL DEFAULT 0,
			cohesion     REAL    NOT NULL DEFAULT 0,
			discipline   REAL    NOT NULL DEFAULT 0,
			redundancy   REAL    NOT NULL DEFAULT 0,
			updated_at   TEXT    NOT NULL
		)`,
	}

	for _, s := range stmts {
		if _, err := db.Exec(s); err != nil {
			return fmt.Errorf("migrate stmt failed: %w\nSQL: %s", err, s)
		}
	}
	return nil
}

// ClearScan 清理某次扫描的全部 arch_* 数据（便于重跑）。
func ClearScan(db *sqlx.DB, scanID int64) error {
	tables := []string{
		"arch_modules", "arch_edges", "arch_cycles",
		"arch_symbols", "arch_calls", "arch_var_refs",
		"arch_patterns", "arch_violations", "arch_hotspots",
		"er_tables", "er_columns", "er_relations",
		"arch_radar",
	}
	tx, err := db.Beginx()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	for _, t := range tables {
		if _, err := tx.Exec(fmt.Sprintf("DELETE FROM %s WHERE scan_id = ?", t), scanID); err != nil {
			return err
		}
	}
	return tx.Commit()
}
