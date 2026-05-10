// Package godclass 用启发式识别「上帝类」「长方法」与产出热点。
//
// 经典阈值参考 Sonar / Fowler 重构经验：
//   - 文件 LOC > 500：godclass-loc 基线
//   - 类方法数 > 25：godclass-methods
//   - 单方法 LOC > 80：longmethod
//   - fan_in > 20 且 fan_out > 10：godclass-coupling（万能依赖）
//
// 命中任意一个维度即视为违规并参与热点打分；
// 严重度按命中维度数量与超阈值幅度综合判定。
package godclass

import (
	"fmt"
	"sort"
	"strings"

	"codeguard/archd/internal/store"
)

// Thresholds 暴露所有阈值，便于将来从 config 注入。
type Thresholds struct {
	ClassLOC     int
	ClassMethods int
	MethodLOC    int
	GodFanIn     int
	GodFanOut    int
	HotspotLimit int
}

// DefaultThresholds 给一组「书本式」默认值。
func DefaultThresholds() Thresholds {
	return Thresholds{
		ClassLOC:     500,
		ClassMethods: 25,
		MethodLOC:    80,
		GodFanIn:     20,
		GodFanOut:    10,
		HotspotLimit: 50,
	}
}

// Result 包含两个产出通道：违规列表与热点列表。
type Result struct {
	Violations []store.Violation
	Hotspots   []store.Hotspot
}

// classKey 锁定「某个文件中名为 X 的类」。
// 提到包级是因为 buildHotspots 需要它做参数。
type classKey struct {
	file string
	name string
}

// Detect 是包级公开入口。
//
// 入参语义：
//
//	modules : 已经回填了 fan_in / fan_out 的模块列表（store.LoadModules 的结果）
//	symbols : 当前扫描的所有符号（class / function / method / interface）
//	th      : 阈值配置
func Detect(scanID int64, modules []store.Module, symbols []store.Symbol, th Thresholds) Result {
	loc := map[string]int{}
	moduleByFile := map[string]string{}
	for _, m := range modules {
		loc[m.FilePath] = m.LOC
		moduleByFile[m.FilePath] = m.ModuleID
	}

	classes := map[classKey]int{}
	classMethods := map[classKey][]store.Symbol{}
	for _, s := range symbols {
		switch s.Kind {
		case "class", "interface", "enum", "record":
			classes[classKey{file: s.FilePath, name: s.Name}] = s.Line
		}
	}
	for _, s := range symbols {
		if s.Kind != "method" || s.Parent == "" {
			continue
		}
		k := classKey{file: s.FilePath, name: s.Parent}
		if _, ok := classes[k]; !ok {
			continue
		}
		classMethods[k] = append(classMethods[k], s)
	}

	type methSpan struct {
		file string
		name string
		par  string
		line int
		span int
	}
	var spans []methSpan
	for k, ms := range classMethods {
		sort.Slice(ms, func(i, j int) bool { return ms[i].Line < ms[j].Line })
		fileLOC := loc[k.file]
		for i, m := range ms {
			next := fileLOC
			if i+1 < len(ms) {
				next = ms[i+1].Line - 1
			}
			span := next - m.Line + 1
			if span < 1 {
				span = 1
			}
			spans = append(spans, methSpan{file: m.FilePath, name: m.Name, par: m.Parent, line: m.Line, span: span})
		}
	}

	var violations []store.Violation

	for _, sp := range spans {
		if sp.span > th.MethodLOC {
			sev := "warning"
			if sp.span > th.MethodLOC*2 {
				sev = "error"
			}
			violations = append(violations, store.Violation{
				ScanID:   scanID,
				Kind:     "longmethod",
				Src:      fmt.Sprintf("%s::%s.%s", sp.file, sp.par, sp.name),
				Severity: sev,
				Detail:   fmt.Sprintf("方法 %s.%s 共约 %d 行，建议拆分（阈值 %d）", sp.par, sp.name, sp.span, th.MethodLOC),
			})
		}
	}

	moduleByName := map[string]store.Module{}
	for _, m := range modules {
		moduleByName[m.ModuleID] = m
	}
	for k, ms := range classMethods {
		fileLOC := loc[k.file]
		methodCount := len(ms)
		mid := moduleByFile[k.file]

		hits := []string{}
		score := 0.0
		if fileLOC > th.ClassLOC {
			hits = append(hits, fmt.Sprintf("LOC=%d>%d", fileLOC, th.ClassLOC))
			score += float64(fileLOC-th.ClassLOC) * 0.05
		}
		if methodCount > th.ClassMethods {
			hits = append(hits, fmt.Sprintf("methods=%d>%d", methodCount, th.ClassMethods))
			score += float64(methodCount-th.ClassMethods) * 0.5
		}
		mod := moduleByName[mid]
		if mod.FanIn > th.GodFanIn && mod.FanOut > th.GodFanOut {
			hits = append(hits, fmt.Sprintf("fan_in=%d>%d ∧ fan_out=%d>%d",
				mod.FanIn, th.GodFanIn, mod.FanOut, th.GodFanOut))
			score += 5
		}
		if len(hits) == 0 {
			continue
		}
		sev := "warning"
		if len(hits) >= 2 || score > 10 {
			sev = "error"
		}
		violations = append(violations, store.Violation{
			ScanID:   scanID,
			Kind:     "godclass",
			Src:      fmt.Sprintf("%s::%s", k.file, k.name),
			Severity: sev,
			Detail:   fmt.Sprintf("上帝类 %s 命中：%s", k.name, strings.Join(hits, "; ")),
		})
	}

	hotspots := buildHotspots(scanID, modules, th)

	return Result{Violations: violations, Hotspots: hotspots}
}

// buildHotspots 给每个模块计算 0~100 的健康分（越低越糟），
// 取最差的前 N 写入 arch_hotspots。
//
// 扣分项：
//   - LOC 超过 ClassLOC 阈值：每超 50 行 -1
//   - fan_in*fan_out 超过 50：每超 10 -1
func buildHotspots(scanID int64, modules []store.Module, th Thresholds) []store.Hotspot {
	type hs struct {
		mid    string
		score  float64
		reason string
	}
	var list []hs
	for _, m := range modules {
		health := 100.0
		var reasons []string
		if m.LOC > th.ClassLOC {
			health -= float64(m.LOC-th.ClassLOC) / 50.0
			reasons = append(reasons, fmt.Sprintf("LOC %d 超过 %d", m.LOC, th.ClassLOC))
		}
		coupling := m.FanIn * m.FanOut
		if coupling > 50 {
			health -= float64(coupling-50) / 10.0
			reasons = append(reasons, fmt.Sprintf("fan_in*fan_out=%d 高耦合", coupling))
		}
		if health > 95 || len(reasons) == 0 {
			continue
		}
		if health < 0 {
			health = 0
		}
		list = append(list, hs{mid: m.ModuleID, score: health, reason: strings.Join(reasons, "; ")})
	}
	sort.Slice(list, func(i, j int) bool { return list[i].score < list[j].score })
	if len(list) > th.HotspotLimit {
		list = list[:th.HotspotLimit]
	}
	out := make([]store.Hotspot, 0, len(list))
	for _, h := range list {
		out = append(out, store.Hotspot{
			ScanID:   scanID,
			ModuleID: h.mid,
			Score:    h.score,
			Reason:   h.reason,
		})
	}
	return out
}
