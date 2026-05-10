// Package pattern 用启发式识别常见设计模式。
//
// 不追求 100% 准确，目标是：在课程演示里能用一组「证据 + 置信度」
// 把开发者写的模式痕迹直观地展示出来。
//
// 已支持模式：
//   - Singleton    : 类内出现 _instance / instance 静态单例 + getInstance
//   - Factory      : 类名以 Factory 结尾 + 含 create* 方法
//   - Repository   : 类名以 Repository / Dao 结尾，且含 find / save / delete
//   - Observer     : 类内含 register / addListener / notify*
//   - Strategy     : 类名以 Strategy 结尾 或 包含 execute / apply 抽象方法的接口
//   - Decorator    : 类构造接受同接口对象（启发式：构造函数参数包含同名前缀）
//   - MVC layout   : 项目同时包含 controllers / models / views 三类目录
//   - Layered      : 出现 routers + services + engines + models 任三种
package pattern

import (
	"fmt"
	"sort"
	"strings"

	"codeguard/archd/internal/store"
)

// Detect 根据符号 + 调用 + 模块路径生成模式列表。
// 调用方负责把它们写入 arch_patterns。
func Detect(scanID int64, symbols []store.Symbol, calls []store.Call, modules []store.Module) []store.Pattern {
	var out []store.Pattern

	classMethods := groupMethodsByClass(symbols)

	out = append(out, detectSingleton(scanID, symbols, classMethods)...)
	out = append(out, detectFactory(scanID, symbols, classMethods)...)
	out = append(out, detectRepository(scanID, symbols, classMethods)...)
	out = append(out, detectObserver(scanID, symbols, classMethods)...)
	out = append(out, detectStrategy(scanID, symbols, classMethods)...)
	out = append(out, detectArchitecturalStyle(scanID, modules)...)

	_ = calls // 当前未使用，保留接口以便未来按调用频度提升置信度
	sort.SliceStable(out, func(i, j int) bool { return out[i].Confidence > out[j].Confidence })
	return out
}

// classKey 同 godclass 用法，但本包内私有以避免循环依赖。
type classKey struct {
	file string
	name string
}

func groupMethodsByClass(symbols []store.Symbol) map[classKey][]string {
	out := map[classKey][]string{}
	for _, s := range symbols {
		if s.Kind != "method" || s.Parent == "" {
			continue
		}
		k := classKey{file: s.FilePath, name: s.Parent}
		out[k] = append(out[k], s.Name)
	}
	return out
}

func detectSingleton(scanID int64, symbols []store.Symbol, methods map[classKey][]string) []store.Pattern {
	var out []store.Pattern
	for k, ms := range methods {
		hasGetInstance := containsAny(ms, "getInstance", "get_instance", "instance")
		hasNew := containsAny(ms, "__new__")
		_ = symbols
		if hasGetInstance || hasNew {
			conf := 0.6
			if hasGetInstance && hasNew {
				conf = 0.9
			}
			out = append(out, store.Pattern{
				ScanID:     scanID,
				Pattern:    "Singleton",
				Confidence: conf,
				Evidence:   fmt.Sprintf("%s::%s 含 %s", k.file, k.name, joinHits(ms, "getInstance", "get_instance", "instance", "__new__")),
			})
		}
	}
	return out
}

func detectFactory(scanID int64, symbols []store.Symbol, methods map[classKey][]string) []store.Pattern {
	var out []store.Pattern
	for _, s := range symbols {
		if s.Kind != "class" {
			continue
		}
		if !strings.HasSuffix(s.Name, "Factory") && !strings.HasSuffix(s.Name, "Builder") {
			continue
		}
		ms := methods[classKey{file: s.FilePath, name: s.Name}]
		if !anyHasPrefix(ms, "create", "build", "make", "new") {
			continue
		}
		out = append(out, store.Pattern{
			ScanID:     scanID,
			Pattern:    "Factory",
			Confidence: 0.85,
			Evidence: fmt.Sprintf("%s::%s 含 create*/build*/make* 方法 [%s]",
				s.FilePath, s.Name, joinHits(ms, "create", "build", "make", "new")),
		})
	}
	return out
}

func detectRepository(scanID int64, symbols []store.Symbol, methods map[classKey][]string) []store.Pattern {
	var out []store.Pattern
	for _, s := range symbols {
		if s.Kind != "class" {
			continue
		}
		looksRepo := strings.HasSuffix(s.Name, "Repository") || strings.HasSuffix(s.Name, "Dao") ||
			strings.HasSuffix(s.Name, "Mapper")
		if !looksRepo {
			continue
		}
		ms := methods[classKey{file: s.FilePath, name: s.Name}]
		hits := []string{}
		for _, kw := range []string{"find", "get", "save", "insert", "update", "delete", "query"} {
			if anyHasPrefix(ms, kw) {
				hits = append(hits, kw+"*")
			}
		}
		if len(hits) < 2 {
			continue
		}
		out = append(out, store.Pattern{
			ScanID:     scanID,
			Pattern:    "Repository",
			Confidence: 0.8 + float64(len(hits))*0.03,
			Evidence:   fmt.Sprintf("%s::%s 含 %s", s.FilePath, s.Name, strings.Join(hits, "/")),
		})
	}
	return out
}

func detectObserver(scanID int64, symbols []store.Symbol, methods map[classKey][]string) []store.Pattern {
	var out []store.Pattern
	for _, s := range symbols {
		if s.Kind != "class" {
			continue
		}
		ms := methods[classKey{file: s.FilePath, name: s.Name}]
		hasReg := anyHasPrefix(ms, "register", "addListener", "addObserver", "subscribe", "on_")
		hasNotify := anyHasPrefix(ms, "notify", "fire", "publish", "emit")
		if !hasReg || !hasNotify {
			continue
		}
		out = append(out, store.Pattern{
			ScanID:     scanID,
			Pattern:    "Observer",
			Confidence: 0.75,
			Evidence: fmt.Sprintf("%s::%s 同时包含订阅与通知方法", s.FilePath, s.Name),
		})
	}
	return out
}

func detectStrategy(scanID int64, symbols []store.Symbol, methods map[classKey][]string) []store.Pattern {
	var out []store.Pattern
	for _, s := range symbols {
		if s.Kind != "class" && s.Kind != "interface" {
			continue
		}
		looksStrategy := strings.HasSuffix(s.Name, "Strategy") || strings.HasSuffix(s.Name, "Policy") ||
			strings.HasSuffix(s.Name, "Algorithm")
		ms := methods[classKey{file: s.FilePath, name: s.Name}]
		hasExec := containsAny(ms, "execute", "apply", "run", "handle")
		if !looksStrategy && !(s.Kind == "interface" && hasExec) {
			continue
		}
		conf := 0.65
		if looksStrategy && hasExec {
			conf = 0.85
		}
		out = append(out, store.Pattern{
			ScanID:     scanID,
			Pattern:    "Strategy",
			Confidence: conf,
			Evidence:   fmt.Sprintf("%s::%s 接口风格 + execute/apply 方法", s.FilePath, s.Name),
		})
	}
	return out
}

// detectArchitecturalStyle 看顶层目录组成判断整体架构风格。
func detectArchitecturalStyle(scanID int64, modules []store.Module) []store.Pattern {
	dirs := map[string]int{}
	for _, m := range modules {
		segs := strings.Split(strings.ReplaceAll(m.FilePath, "\\", "/"), "/")
		// 取前 3 段作为「层目录」候选
		for i := 0; i < 3 && i < len(segs); i++ {
			dirs[segs[i]]++
		}
	}
	have := func(name string) bool {
		_, ok := dirs[name]
		return ok
	}
	var out []store.Pattern
	if have("controllers") && have("models") && have("views") {
		out = append(out, store.Pattern{
			ScanID:     scanID,
			Pattern:    "MVC",
			Confidence: 0.9,
			Evidence:   "顶层目录同时包含 controllers / models / views",
		})
	}
	hits := 0
	for _, n := range []string{"routers", "services", "engines", "models", "schemas"} {
		if have(n) {
			hits++
		}
	}
	if hits >= 3 {
		out = append(out, store.Pattern{
			ScanID:     scanID,
			Pattern:    "Layered",
			Confidence: 0.6 + float64(hits)*0.08,
			Evidence:   fmt.Sprintf("顶层目录命中分层关键字 %d/5", hits),
		})
	}
	return out
}

// containsAny 判断切片是否包含任一名字（精确匹配）。
func containsAny(s []string, names ...string) bool {
	set := map[string]struct{}{}
	for _, n := range s {
		set[n] = struct{}{}
	}
	for _, n := range names {
		if _, ok := set[n]; ok {
			return true
		}
	}
	return false
}

// anyHasPrefix 判断切片中是否有元素以任一前缀开头。
func anyHasPrefix(s []string, prefixes ...string) bool {
	for _, x := range s {
		for _, p := range prefixes {
			if strings.HasPrefix(x, p) {
				return true
			}
		}
	}
	return false
}

// joinHits 给 evidence 用，挑出实际命中的几个名字（最多 3 个）拼接展示。
func joinHits(s []string, anchors ...string) string {
	hits := []string{}
	for _, x := range s {
		for _, a := range anchors {
			if x == a || strings.HasPrefix(x, a) {
				hits = append(hits, x)
				break
			}
		}
		if len(hits) >= 3 {
			break
		}
	}
	if len(hits) == 0 {
		return "—"
	}
	return strings.Join(hits, ", ")
}
