// Package main 的分析模块端到端测试：对项目自身后端目录跑全链路。
//
// 验证：
//   - 解析后能产出 modules / edges
//   - SCC 与 cycle 检测可以稳定运行
//   - layer / godclass / pattern / radar 不会 panic、产出形状合法
//
// 不断言「某条具体违规存在」，因为业务代码会演进；
// 这个测试是「pipeline 健壮性」检查。
package main

import (
	"testing"

	"codeguard/archd/internal/cycle"
	"codeguard/archd/internal/godclass"
	"codeguard/archd/internal/layer"
	"codeguard/archd/internal/overeng"
	"codeguard/archd/internal/parser"
	"codeguard/archd/internal/pattern"
	"codeguard/archd/internal/radar"
	"codeguard/archd/internal/store"
)

func TestPipelineOnBackend(t *testing.T) {
	root := findRepoRoot(t)
	// 扫 项目根：这样 moduleID 是 "backend.config" 之类，
	// 与源码内 "from backend.config" 的写法对得上、能解析为 import 边
	res, err := parser.Parse(parser.ParseOptions{
		Root:           root,
		AllowLanguages: []string{"python"},
	})
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if len(res.Modules) < 5 {
		t.Fatalf("modules=%d, expected >= 5 for Python backend", len(res.Modules))
	}
	if len(res.Edges) == 0 {
		t.Fatalf("edges=0; parser failed to resolve any import — likely module-id naming mismatch")
	}

	// 计算并回填 fan_in / fan_out + layer
	fanIn := map[string]int{}
	fanOut := map[string]int{}
	for _, e := range res.Edges {
		fanOut[e.Src]++
		fanIn[e.Dst]++
	}
	for i := range res.Modules {
		res.Modules[i].FanIn = fanIn[res.Modules[i].ModuleID]
		res.Modules[i].FanOut = fanOut[res.Modules[i].ModuleID]
	}
	layers := layer.AssignLayers(res.Modules)
	for i := range res.Modules {
		res.Modules[i].Layer = layers[res.Modules[i].ModuleID]
	}

	cycles := cycle.Detect(0, res.Edges)
	gc := godclass.Detect(0, res.Modules, res.Symbols, godclass.DefaultThresholds())
	oe := overeng.Detect(0, res.Symbols, res.Edges, overeng.DefaultThresholds())
	lv := layer.DetectViolations(0, res.Edges)
	patterns := pattern.Detect(0, res.Symbols, res.Calls, res.Modules)

	violations := make([]store.Violation, 0, len(gc.Violations)+len(oe)+len(lv))
	violations = append(violations, gc.Violations...)
	violations = append(violations, oe...)
	violations = append(violations, lv...)

	rad := radar.Compute(0, radar.Inputs{
		Modules:    res.Modules,
		Edges:      res.Edges,
		Symbols:    res.Symbols,
		Cycles:     cycles,
		Violations: violations,
		Patterns:   patterns,
	})

	overall := radar.Overall(rad)
	if overall < 0 || overall > 100 {
		t.Fatalf("overall score out of range: %.2f", overall)
	}
	t.Logf("overall=%.2f modules=%d edges=%d cycles=%d violations=%d patterns=%d hotspots=%d",
		overall, len(res.Modules), len(res.Edges), len(cycles), len(violations), len(patterns), len(gc.Hotspots))
}
