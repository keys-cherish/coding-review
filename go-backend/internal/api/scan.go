// Package api 中：扫描编排器（orchestrator）。
//
// 职责：把 parser → 各分析模块 → store 串起来。
// 设计：
//   - 单次 RunScan 是同步的，调用方（Gin handler）持有请求生命周期。
//     课程项目里项目体量小（千行级），同步处理足够；
//     大项目可后续把这里换为 goroutine + channel + WS 推进度。
//   - 任何阶段失败都让 RunScan 返回 error，外层 handler 渲染 500；
//     已经写入的数据会被下一次 ClearScan 清掉，不会影响一致性。
package api

import (
	"fmt"
	"path/filepath"

	"github.com/jmoiron/sqlx"

	"codeguard/archd/internal/cycle"
	"codeguard/archd/internal/godclass"
	"codeguard/archd/internal/layer"
	"codeguard/archd/internal/overeng"
	"codeguard/archd/internal/parser"
	"codeguard/archd/internal/pattern"
	"codeguard/archd/internal/radar"
	"codeguard/archd/internal/store"
)

// ScanReport 是 POST /scan/:scan_id 的返回体，给前端做实时反馈。
type ScanReport struct {
	ScanID         int64  `json:"scan_id"`
	UploadPath     string `json:"upload_path"`
	FilesScanned   int    `json:"files_scanned"`
	FilesSkipped   int    `json:"files_skipped"`
	Modules        int    `json:"modules"`
	Edges          int    `json:"edges"`
	Symbols        int    `json:"symbols"`
	Cycles         int    `json:"cycles"`
	Violations     int    `json:"violations"`
	Patterns       int    `json:"patterns"`
	Hotspots       int    `json:"hotspots"`
	OverallScore   float64 `json:"overall_score"`
}

// RunScan 跑完一次扫描全流程。
//
// 步骤：
//  1. 反查 scan_id → version 上传目录
//  2. 清掉之前的 arch_* 数据
//  3. parser.Parse → 写入 modules/edges/symbols/calls/var_refs
//  4. 拉回 modules+edges 计算 fan_in/fan_out → 回填
//  5. 推断 layer → 回填
//  6. cycle / godclass / overeng / layer-violations / pattern → 写各自表
//  7. radar.Compute → 写 arch_radar
//  8. 返回 ScanReport
func RunScan(db *sqlx.DB, scanID int64) (*ScanReport, error) {
	v, err := store.LoadVersionByScanID(db, scanID)
	if err != nil {
		return nil, fmt.Errorf("load version: %w", err)
	}
	if !filepath.IsAbs(v.UploadPath) {
		// Python 端写入时通常是相对路径，相对于「项目根 = archd 进程的 ../」
		// 由 main.go 通过 CODEGUARD_DB / 工作目录决定基准；这里再加一次容错。
		abs, err := filepath.Abs(v.UploadPath)
		if err == nil {
			v.UploadPath = abs
		}
	}

	if err := store.ClearScan(db, scanID); err != nil {
		return nil, fmt.Errorf("clear: %w", err)
	}

	res, err := parser.Parse(parser.ParseOptions{
		Root:    v.UploadPath,
		ScanID:  scanID,
	})
	if err != nil {
		return nil, fmt.Errorf("parse: %w", err)
	}

	if err := store.InsertModulesBatch(db, res.Modules); err != nil {
		return nil, fmt.Errorf("save modules: %w", err)
	}
	if err := store.InsertEdgesBatch(db, res.Edges); err != nil {
		return nil, fmt.Errorf("save edges: %w", err)
	}
	if err := store.InsertSymbolsBatch(db, res.Symbols); err != nil {
		return nil, fmt.Errorf("save symbols: %w", err)
	}
	if err := store.InsertCallsBatch(db, res.Calls); err != nil {
		return nil, fmt.Errorf("save calls: %w", err)
	}
	if err := store.InsertVarRefsBatch(db, res.VarRefs); err != nil {
		return nil, fmt.Errorf("save var refs: %w", err)
	}

	// 计算 fan_in / fan_out，写回模块表
	fanIn := map[string]int{}
	fanOut := map[string]int{}
	for _, e := range res.Edges {
		if e.Kind != "import" {
			continue
		}
		fanOut[e.Src]++
		fanIn[e.Dst]++
	}
	if err := store.UpdateModuleFanInOut(db, scanID, fanIn, fanOut); err != nil {
		return nil, fmt.Errorf("update fan: %w", err)
	}

	// 重新加载 modules（带 fan_in/fan_out），后续分析直接用
	modules, err := store.LoadModules(db, scanID)
	if err != nil {
		return nil, fmt.Errorf("reload modules: %w", err)
	}

	// 分层
	layers := layer.AssignLayers(modules)
	if err := store.UpdateModuleLayer(db, scanID, layers); err != nil {
		return nil, fmt.Errorf("update layer: %w", err)
	}
	for i := range modules {
		modules[i].Layer = layers[modules[i].ModuleID]
	}

	// 各分析模块
	cycles := cycle.Detect(scanID, res.Edges)
	if err := store.InsertCyclesBatch(db, cycles); err != nil {
		return nil, fmt.Errorf("save cycles: %w", err)
	}

	gc := godclass.Detect(scanID, modules, res.Symbols, godclass.DefaultThresholds())
	oe := overeng.Detect(scanID, res.Symbols, res.Edges, overeng.DefaultThresholds())
	lv := layer.DetectViolations(scanID, res.Edges)

	allViolations := make([]store.Violation, 0, len(gc.Violations)+len(oe)+len(lv))
	allViolations = append(allViolations, gc.Violations...)
	allViolations = append(allViolations, oe...)
	allViolations = append(allViolations, lv...)
	if err := store.InsertViolationsBatch(db, allViolations); err != nil {
		return nil, fmt.Errorf("save violations: %w", err)
	}
	if err := store.InsertHotspotsBatch(db, gc.Hotspots); err != nil {
		return nil, fmt.Errorf("save hotspots: %w", err)
	}

	patterns := pattern.Detect(scanID, res.Symbols, res.Calls, modules)
	if err := store.InsertPatternsBatch(db, patterns); err != nil {
		return nil, fmt.Errorf("save patterns: %w", err)
	}

	rad := radar.Compute(scanID, radar.Inputs{
		Modules:    modules,
		Edges:      res.Edges,
		Symbols:    res.Symbols,
		Cycles:     cycles,
		Violations: allViolations,
		Patterns:   patterns,
	})
	if err := store.UpsertRadar(db, rad); err != nil {
		return nil, fmt.Errorf("save radar: %w", err)
	}

	return &ScanReport{
		ScanID:       scanID,
		UploadPath:   v.UploadPath,
		FilesScanned: res.FilesScanned,
		FilesSkipped: res.FilesSkipped,
		Modules:      len(res.Modules),
		Edges:        len(res.Edges),
		Symbols:      len(res.Symbols),
		Cycles:       len(cycles),
		Violations:   len(allViolations),
		Patterns:     len(patterns),
		Hotspots:     len(gc.Hotspots),
		OverallScore: radar.Overall(rad),
	}, nil
}
