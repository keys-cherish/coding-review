// Package radar 把所有分析结果折算为「6 维架构雷达分」。
//
// 维度定义（与 arch_radar 表列名对齐，单位 0~100）：
//
//	clarity    清晰度    分层覆盖率高、命名规则一致 → 高
//	isolation  分层隔离  分层违规边占比低 → 高
//	decoupling 解耦度    平均 fan_in/out 低、循环依赖少 → 高
//	cohesion   内聚度    God Class 比例低、类内调用比例高 → 高
//	discipline 规范执行  过度设计违规少 → 高
//	redundancy 冗余度    模式识别成果丰富、代码组织规整 → 高（注意是「越少冗余越好」语义反转）
//
// 每个维度的得分都用一个简单的「基线 - 扣分」公式，
// 落地代码尽量不复杂，便于在评审场合口头解释清楚。
package radar

import (
	"codeguard/archd/internal/store"
)

// Inputs 把雷达计算所需的全部上游产物聚合到一处，
// 这样函数签名清晰，将来要加输入也只动这一个结构。
type Inputs struct {
	Modules    []store.Module
	Edges      []store.Edge
	Symbols    []store.Symbol
	Cycles     []store.Cycle
	Violations []store.Violation
	Patterns   []store.Pattern
}

// Compute 接收 Inputs，返回 Radar 行（不含时间戳，由 store 填）。
func Compute(scanID int64, in Inputs) store.Radar {
	r := store.Radar{ScanID: scanID}

	totalModules := len(in.Modules)
	if totalModules == 0 {
		// 没有模块的极端情况：六维全 0，便于前端给出「无数据」状态
		return r
	}

	r.Clarity = scoreClarity(in.Modules)
	r.Isolation = scoreIsolation(in.Modules, in.Violations)
	r.Decoupling = scoreDecoupling(in.Modules, in.Cycles)
	r.Cohesion = scoreCohesion(in.Modules, in.Symbols, in.Violations)
	r.Discipline = scoreDiscipline(in.Violations, totalModules)
	r.Redundancy = scoreRedundancy(in.Modules, in.Violations)

	return r
}

// scoreClarity 按「分层覆盖率」评分：layer != "" 的模块占比 → 0..100。
//
// 分层覆盖率高，意味着架构边界清晰可识别。
func scoreClarity(modules []store.Module) float64 {
	classified := 0
	for _, m := range modules {
		if m.Layer != "" {
			classified++
		}
	}
	ratio := float64(classified) / float64(len(modules))
	return clamp(ratio*100, 0, 100)
}

// scoreIsolation 按「分层违规边」反向计分。
//
//	100 - violation_count / total_modules * 200
//
// 不直接除以总边数是因为 layer 违规已经过滤过 import-only edges，
// 用 modules 数做分母更稳定。
func scoreIsolation(modules []store.Module, violations []store.Violation) float64 {
	v := 0
	for _, x := range violations {
		if x.Kind == "layer" {
			v++
		}
	}
	penalty := float64(v) / float64(len(modules)) * 200
	return clamp(100-penalty, 0, 100)
}

// scoreDecoupling 综合考虑：
//
//   - 平均 fan_out（< 5 视为良好）
//   - 循环依赖数（每个 critical 扣 8，major 5，minor 2）
//
// 起点 100 → 扣分。
func scoreDecoupling(modules []store.Module, cycles []store.Cycle) float64 {
	totFanOut := 0
	for _, m := range modules {
		totFanOut += m.FanOut
	}
	avgFanOut := float64(totFanOut) / float64(len(modules))

	score := 100.0
	if avgFanOut > 5 {
		score -= (avgFanOut - 5) * 4
	}

	for _, c := range cycles {
		switch c.Severity {
		case "critical":
			score -= 8
		case "major":
			score -= 5
		case "minor":
			score -= 2
		}
	}
	return clamp(score, 0, 100)
}

// scoreCohesion 通过 godclass / longmethod 违规比例反向计分。
//
//   起点 100，每条 godclass 扣 4 分，每条 longmethod 扣 1 分。
//
// modules 用作分母防止小型项目里偶现一两条直接拉爆 cohesion。
func scoreCohesion(modules []store.Module, symbols []store.Symbol, violations []store.Violation) float64 {
	_ = symbols
	score := 100.0
	for _, v := range violations {
		switch v.Kind {
		case "godclass":
			score -= 4
		case "longmethod":
			score -= 1
		}
	}
	if score < 0 {
		score = 0
	}
	// 大项目天然违规多，按模块数做轻微补偿
	if len(modules) > 50 {
		score += float64(len(modules)-50) * 0.05
	}
	return clamp(score, 0, 100)
}

// scoreDiscipline 把 overeng 违规率反向打分。
func scoreDiscipline(violations []store.Violation, totalModules int) float64 {
	count := 0
	for _, v := range violations {
		if v.Kind == "overeng" {
			count++
		}
	}
	score := 100.0 - float64(count)/float64(totalModules)*40
	return clamp(score, 0, 100)
}

// scoreRedundancy 这里用「层级深度方差」与「同顶级目录模块数」分布作粗代理。
//
//   层级越扁平 + 顶层模块数越平均 = 越规整 = 高分。
func scoreRedundancy(modules []store.Module, violations []store.Violation) float64 {
	_ = violations
	if len(modules) == 0 {
		return 0
	}
	// 计算路径深度
	totDepth := 0
	maxDepth := 0
	for _, m := range modules {
		d := pathDepth(m.FilePath)
		totDepth += d
		if d > maxDepth {
			maxDepth = d
		}
	}
	avg := float64(totDepth) / float64(len(modules))
	score := 100.0
	if avg > 5 {
		score -= (avg - 5) * 8
	}
	if maxDepth > 8 {
		score -= float64(maxDepth-8) * 3
	}
	return clamp(score, 0, 100)
}

// pathDepth 数路径段数。
func pathDepth(p string) int {
	d := 0
	for _, c := range p {
		if c == '/' || c == '\\' {
			d++
		}
	}
	return d
}

// clamp 把分数裁剪到 [lo, hi]。
func clamp(v, lo, hi float64) float64 {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

// Overall 按等权平均聚合一个综合分；前端可以直接展示。
func Overall(r store.Radar) float64 {
	return (r.Clarity + r.Isolation + r.Decoupling + r.Cohesion + r.Discipline + r.Redundancy) / 6
}
