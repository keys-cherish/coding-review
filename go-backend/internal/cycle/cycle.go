// Package cycle 利用图算法识别模块级循环依赖，
// 并把每个 SCC 转换为可读的 Cycle 记录写入 arch_cycles。
//
// 严重度判定（与课程评分维度直接对齐）：
//   - critical: SCC 体积 ≥ 6，或包含 wildcard import（破坏力大）
//   - major:    SCC 体积 3~5
//   - minor:    SCC 体积 = 2（最常见的「双向耦合」）
//
// 体积更小（=1）的孤立顶点会被 Tarjan 当成自己的 SCC，被本包过滤。
package cycle

import (
	"encoding/json"
	"fmt"

	"codeguard/archd/internal/graph"
	"codeguard/archd/internal/store"
)

// Detect 把 edges 折叠为图，跑 Tarjan，提取 size>=2 的 SCC，
// 同时为每个 SCC 计算「最短回路示例」便于前端展示。
//
// scanID 用于在结果上打标签；返回的 Cycle 可直接 InsertCyclesBatch。
func Detect(scanID int64, edges []store.Edge) []store.Cycle {
	g := graph.New()
	wildcard := map[string]bool{} // src->dst pair 是否含通配
	for _, e := range edges {
		if e.Kind != "import" && e.Kind != "inherit" {
			continue
		}
		g.AddEdge(e.Src, e.Dst, e.Count)
		if e.IsWildcard != 0 {
			wildcard[e.Src+"->"+e.Dst] = true
		}
	}

	sccs := g.SCC()
	var out []store.Cycle
	for _, comp := range sccs {
		if len(comp) < 2 {
			continue
		}
		hasWildcard := false
		inComp := map[string]bool{}
		for _, n := range comp {
			inComp[n] = true
		}
		for _, src := range comp {
			for _, dst := range g.OutNeighbors(src) {
				if !inComp[dst] {
					continue
				}
				if wildcard[src+"->"+dst] {
					hasWildcard = true
					break
				}
			}
			if hasWildcard {
				break
			}
		}

		modulesJSON, _ := json.Marshal(comp)

		// 取分量内首个节点作为切入点，找一条最短回路
		example := g.ShortestCycleThrough(comp[0])
		if example == nil {
			example = comp // fallback：直接给出成员列表
		}
		pathJSON, _ := json.Marshal(example)

		out = append(out, store.Cycle{
			ScanID:      scanID,
			Size:        len(comp),
			Severity:    classify(len(comp), hasWildcard),
			ModulesJSON: string(modulesJSON),
			PathJSON:    string(pathJSON),
		})
	}
	return out
}

// classify 把（size, 是否含通配）映射到三级严重度。
func classify(size int, hasWildcard bool) string {
	if hasWildcard || size >= 6 {
		return "critical"
	}
	if size >= 3 {
		return "major"
	}
	return "minor"
}

// SummaryLine 提供给日志 / 调试用，返回单行人类可读总结。
func SummaryLine(cycles []store.Cycle) string {
	if len(cycles) == 0 {
		return "no cycles"
	}
	by := map[string]int{}
	for _, c := range cycles {
		by[c.Severity]++
	}
	return fmt.Sprintf("cycles=%d (critical=%d, major=%d, minor=%d)",
		len(cycles), by["critical"], by["major"], by["minor"])
}
