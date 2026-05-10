// Package store 中针对 arch_* 表的批量写入助手。
//
// 设计取舍：所有 InsertXxxBatch 都在单事务内完成，以保证一次扫描
// 落库的原子性 —— 要么完整可读，要么连残片都不会留。
package store

import (
	"database/sql"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
)

// withTx 把一组 SQL 操作打包到一个事务里，失败自动回滚。
func withTx(db *sqlx.DB, fn func(tx *sqlx.Tx) error) error {
	tx, err := db.Beginx()
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	if err := fn(tx); err != nil {
		_ = tx.Rollback()
		return err
	}
	return tx.Commit()
}

// InsertModulesBatch 批量写入 arch_modules（OR REPLACE 以支持重跑覆盖）。
func InsertModulesBatch(db *sqlx.DB, mods []Module) error {
	if len(mods) == 0 {
		return nil
	}
	const q = `INSERT OR REPLACE INTO arch_modules
		(scan_id, module_id, file_path, language, loc, fan_in, fan_out, layer)
		VALUES (:scan_id, :module_id, :file_path, :language, :loc, :fan_in, :fan_out, :layer)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, m := range mods {
			if _, err := tx.NamedExec(q, m); err != nil {
				return fmt.Errorf("insert module %s: %w", m.ModuleID, err)
			}
		}
		return nil
	})
}

// InsertEdgesBatch 批量写入 arch_edges，相同 (src,dst,kind) 累加 count。
func InsertEdgesBatch(db *sqlx.DB, edges []Edge) error {
	if len(edges) == 0 {
		return nil
	}
	const q = `INSERT INTO arch_edges
		(scan_id, src, dst, kind, count, is_wildcard)
		VALUES (:scan_id, :src, :dst, :kind, :count, :is_wildcard)
		ON CONFLICT(scan_id, src, dst, kind) DO UPDATE SET
		count = count + excluded.count,
		is_wildcard = MAX(is_wildcard, excluded.is_wildcard)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, e := range edges {
			if _, err := tx.NamedExec(q, e); err != nil {
				return fmt.Errorf("insert edge %s->%s: %w", e.Src, e.Dst, err)
			}
		}
		return nil
	})
}

// InsertSymbolsBatch 写入 arch_symbols。
func InsertSymbolsBatch(db *sqlx.DB, syms []Symbol) error {
	if len(syms) == 0 {
		return nil
	}
	const q = `INSERT INTO arch_symbols
		(scan_id, name, kind, file_path, line, parent)
		VALUES (:scan_id, :name, :kind, :file_path, :line, :parent)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, s := range syms {
			if _, err := tx.NamedExec(q, s); err != nil {
				return err
			}
		}
		return nil
	})
}

// InsertCallsBatch 写入 arch_calls。
func InsertCallsBatch(db *sqlx.DB, calls []Call) error {
	if len(calls) == 0 {
		return nil
	}
	const q = `INSERT INTO arch_calls
		(scan_id, caller, callee, file_path, line)
		VALUES (:scan_id, :caller, :callee, :file_path, :line)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, c := range calls {
			if _, err := tx.NamedExec(q, c); err != nil {
				return err
			}
		}
		return nil
	})
}

// InsertVarRefsBatch 写入 arch_var_refs。
func InsertVarRefsBatch(db *sqlx.DB, refs []VarRef) error {
	if len(refs) == 0 {
		return nil
	}
	const q = `INSERT INTO arch_var_refs
		(scan_id, var_name, action, file_path, line)
		VALUES (:scan_id, :var_name, :action, :file_path, :line)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, r := range refs {
			if _, err := tx.NamedExec(q, r); err != nil {
				return err
			}
		}
		return nil
	})
}

// InsertCyclesBatch 写入 arch_cycles。
func InsertCyclesBatch(db *sqlx.DB, cycles []Cycle) error {
	if len(cycles) == 0 {
		return nil
	}
	const q = `INSERT INTO arch_cycles
		(scan_id, size, severity, modules_json, path_json)
		VALUES (:scan_id, :size, :severity, :modules_json, :path_json)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, c := range cycles {
			if _, err := tx.NamedExec(q, c); err != nil {
				return err
			}
		}
		return nil
	})
}

// InsertPatternsBatch 写入 arch_patterns。
func InsertPatternsBatch(db *sqlx.DB, ps []Pattern) error {
	if len(ps) == 0 {
		return nil
	}
	const q = `INSERT INTO arch_patterns
		(scan_id, pattern, confidence, evidence)
		VALUES (:scan_id, :pattern, :confidence, :evidence)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, p := range ps {
			if _, err := tx.NamedExec(q, p); err != nil {
				return err
			}
		}
		return nil
	})
}

// InsertViolationsBatch 写入 arch_violations。
func InsertViolationsBatch(db *sqlx.DB, vs []Violation) error {
	if len(vs) == 0 {
		return nil
	}
	const q = `INSERT INTO arch_violations
		(scan_id, kind, src, dst, severity, detail)
		VALUES (:scan_id, :kind, :src, :dst, :severity, :detail)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, v := range vs {
			if _, err := tx.NamedExec(q, v); err != nil {
				return err
			}
		}
		return nil
	})
}

// InsertHotspotsBatch 写入 arch_hotspots。
func InsertHotspotsBatch(db *sqlx.DB, hs []Hotspot) error {
	if len(hs) == 0 {
		return nil
	}
	const q = `INSERT INTO arch_hotspots
		(scan_id, module_id, score, reason)
		VALUES (:scan_id, :module_id, :score, :reason)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, h := range hs {
			if _, err := tx.NamedExec(q, h); err != nil {
				return err
			}
		}
		return nil
	})
}

// UpsertRadar 重置一次扫描的雷达分数（一对一）。
func UpsertRadar(db *sqlx.DB, r Radar) error {
	if r.UpdatedAt == "" {
		r.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	}
	const q = `INSERT OR REPLACE INTO arch_radar
		(scan_id, clarity, isolation, decoupling, cohesion, discipline, redundancy, updated_at)
		VALUES (:scan_id, :clarity, :isolation, :decoupling, :cohesion, :discipline, :redundancy, :updated_at)`
	_, err := db.NamedExec(q, r)
	return err
}

// InsertERTablesBatch / InsertERColumnsBatch / InsertERRelationsBatch
// 共同维护推断出来的 ER 模型；表按 (scan_id, table_name) 唯一。
func InsertERTablesBatch(db *sqlx.DB, ts []ERTable) error {
	if len(ts) == 0 {
		return nil
	}
	const q = `INSERT OR REPLACE INTO er_tables
		(scan_id, table_name, source_file)
		VALUES (:scan_id, :table_name, :source_file)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, t := range ts {
			if _, err := tx.NamedExec(q, t); err != nil {
				return err
			}
		}
		return nil
	})
}

func InsertERColumnsBatch(db *sqlx.DB, cs []ERColumn) error {
	if len(cs) == 0 {
		return nil
	}
	const q = `INSERT OR REPLACE INTO er_columns
		(scan_id, table_name, col_name, col_type, is_pk, is_fk, fk_table, fk_col)
		VALUES (:scan_id, :table_name, :col_name, :col_type, :is_pk, :is_fk, :fk_table, :fk_col)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, c := range cs {
			if _, err := tx.NamedExec(q, c); err != nil {
				return err
			}
		}
		return nil
	})
}

func InsertERRelationsBatch(db *sqlx.DB, rs []ERRelation) error {
	if len(rs) == 0 {
		return nil
	}
	const q = `INSERT INTO er_relations
		(scan_id, from_table, to_table, kind)
		VALUES (:scan_id, :from_table, :to_table, :kind)`
	return withTx(db, func(tx *sqlx.Tx) error {
		for _, r := range rs {
			if _, err := tx.NamedExec(q, r); err != nil {
				return err
			}
		}
		return nil
	})
}

// LoadVersionByScanID 通过 scan_id 反查 versions 行，得到 upload_path 与项目 ID。
func LoadVersionByScanID(db *sqlx.DB, scanID int64) (*VersionInfo, error) {
	const q = `SELECT v.id, v.project_id, v.upload_path, v.uploaded_at
		FROM versions v JOIN scan_tasks t ON t.version_id = v.id
		WHERE t.id = ?`
	var v VersionInfo
	if err := db.Get(&v, q, scanID); err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("scan_id %d not found", scanID)
		}
		return nil, fmt.Errorf("query version: %w", err)
	}
	return &v, nil
}

// LoadSourceFiles 列出某个 version 关联的全部源文件。
func LoadSourceFiles(db *sqlx.DB, versionID int64) ([]SourceFileInfo, error) {
	const q = `SELECT id, version_id, relative_path, language, lines_of_code, total_lines
		FROM source_files WHERE version_id = ? ORDER BY relative_path`
	var rows []SourceFileInfo
	if err := db.Select(&rows, q, versionID); err != nil {
		return nil, fmt.Errorf("load source files: %w", err)
	}
	return rows, nil
}

// LoadModules 拉取一次扫描的全部模块；分析模块需要邻接表时使用。
func LoadModules(db *sqlx.DB, scanID int64) ([]Module, error) {
	var rows []Module
	if err := db.Select(&rows, `SELECT scan_id, module_id, file_path, language, loc, fan_in, fan_out, layer
		FROM arch_modules WHERE scan_id = ?`, scanID); err != nil {
		return nil, err
	}
	return rows, nil
}

// LoadEdges 拉取一次扫描的全部边。
func LoadEdges(db *sqlx.DB, scanID int64) ([]Edge, error) {
	var rows []Edge
	if err := db.Select(&rows, `SELECT scan_id, src, dst, kind, count, is_wildcard
		FROM arch_edges WHERE scan_id = ?`, scanID); err != nil {
		return nil, err
	}
	return rows, nil
}

// UpdateModuleFanInOut 把统计好的入度出度回填到 arch_modules。
func UpdateModuleFanInOut(db *sqlx.DB, scanID int64, fanIn, fanOut map[string]int) error {
	const q = `UPDATE arch_modules SET fan_in = ?, fan_out = ?
		WHERE scan_id = ? AND module_id = ?`
	return withTx(db, func(tx *sqlx.Tx) error {
		mods := make(map[string]struct{})
		for k := range fanIn {
			mods[k] = struct{}{}
		}
		for k := range fanOut {
			mods[k] = struct{}{}
		}
		for m := range mods {
			if _, err := tx.Exec(q, fanIn[m], fanOut[m], scanID, m); err != nil {
				return err
			}
		}
		return nil
	})
}

// UpdateModuleLayer 把推断出的分层信息回填到 arch_modules.layer。
func UpdateModuleLayer(db *sqlx.DB, scanID int64, layers map[string]string) error {
	const q = `UPDATE arch_modules SET layer = ? WHERE scan_id = ? AND module_id = ?`
	return withTx(db, func(tx *sqlx.Tx) error {
		for m, layer := range layers {
			if _, err := tx.Exec(q, layer, scanID, m); err != nil {
				return err
			}
		}
		return nil
	})
}

// LoadSymbols 拉取一次扫描的全部符号。
func LoadSymbols(db *sqlx.DB, scanID int64) ([]Symbol, error) {
	var rows []Symbol
	if err := db.Select(&rows, `SELECT id, scan_id, name, kind, file_path, line, parent
		FROM arch_symbols WHERE scan_id = ?`, scanID); err != nil {
		return nil, err
	}
	return rows, nil
}

// LoadCalls 拉取一次扫描的全部 call 边。
func LoadCalls(db *sqlx.DB, scanID int64) ([]Call, error) {
	var rows []Call
	if err := db.Select(&rows, `SELECT id, scan_id, caller, callee, file_path, line
		FROM arch_calls WHERE scan_id = ?`, scanID); err != nil {
		return nil, err
	}
	return rows, nil
}

// LoadCycles / LoadViolations / LoadPatterns / LoadHotspots / LoadRadar
// 是 api 层的只读查询。
func LoadCycles(db *sqlx.DB, scanID int64) ([]Cycle, error) {
	var rows []Cycle
	err := db.Select(&rows, `SELECT id, scan_id, size, severity, modules_json, path_json
		FROM arch_cycles WHERE scan_id = ? ORDER BY size DESC`, scanID)
	return rows, err
}

func LoadViolations(db *sqlx.DB, scanID int64) ([]Violation, error) {
	var rows []Violation
	err := db.Select(&rows, `SELECT id, scan_id, kind, src, dst, severity, detail
		FROM arch_violations WHERE scan_id = ? ORDER BY kind, severity`, scanID)
	return rows, err
}

func LoadPatterns(db *sqlx.DB, scanID int64) ([]Pattern, error) {
	var rows []Pattern
	err := db.Select(&rows, `SELECT id, scan_id, pattern, confidence, evidence
		FROM arch_patterns WHERE scan_id = ? ORDER BY confidence DESC`, scanID)
	return rows, err
}

func LoadHotspots(db *sqlx.DB, scanID int64) ([]Hotspot, error) {
	var rows []Hotspot
	err := db.Select(&rows, `SELECT id, scan_id, module_id, score, reason
		FROM arch_hotspots WHERE scan_id = ? ORDER BY score ASC LIMIT 50`, scanID)
	return rows, err
}

func LoadRadar(db *sqlx.DB, scanID int64) (*Radar, error) {
	var r Radar
	err := db.Get(&r, `SELECT scan_id, clarity, isolation, decoupling, cohesion, discipline, redundancy, updated_at
		FROM arch_radar WHERE scan_id = ?`, scanID)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &r, nil
}
