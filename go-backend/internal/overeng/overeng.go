// Package overeng 识别一些「过度设计」反模式：
//
//   - Java：interface / abstract class 仅有 ≤1 个具体实现
//     （除工厂 / 策略类的「未来扩展」声明外，多数是抽象冗余）
//   - 命名爆炸：以 Manager / Helper / Util / Wrapper / Provider 结尾
//     的类型 ≥ 阈值（这些命名通常是把责任「打包推走」的烟雾弹）
//   - 多重继承层级：Python class 父类显式声明 ≥3 时给一个提示
//
// 这些规则不在课程评分硬指标里，但能强化「架构智能」演示效果。
package overeng

import (
	"fmt"
	"strings"

	"codeguard/archd/internal/store"
)

// NamingNoise 是「过度命名」黑名单。命中后只是计入计数，
// 当一类项目同后缀类型超过阈值才报。
var NamingNoise = []string{"Manager", "Helper", "Util", "Utils", "Wrapper", "Provider", "Service", "Handler"}

// Thresholds 把硬编码集中起来。
type Thresholds struct {
	NoiseSameSuffix    int // 同后缀计数阈值
	MaxParents         int // Python 多重继承层级
	MinAbstractCallers int // interface / abstract 至少应被 N 个类引用才算「合理」
}

// DefaultThresholds 适合中型项目的默认值。
func DefaultThresholds() Thresholds {
	return Thresholds{
		NoiseSameSuffix:    8,
		MaxParents:         3,
		MinAbstractCallers: 2,
	}
}

// Detect 跑全部检查并返回违规列表。
//
// 入参语义：
//
//	symbols : 全部符号（class / interface / method 等）
//	edges   : 模块/继承边（用来推断 interface 是否被实现）
func Detect(scanID int64, symbols []store.Symbol, edges []store.Edge, th Thresholds) []store.Violation {
	var out []store.Violation
	out = append(out, detectNamingNoise(scanID, symbols, th)...)
	out = append(out, detectAbstractWithoutImpl(scanID, symbols, edges, th)...)
	out = append(out, detectDeepInheritance(scanID, symbols, edges, th)...)
	return out
}

// detectNamingNoise 按后缀分类计数，超阈值的后缀产出一条 violation。
func detectNamingNoise(scanID int64, symbols []store.Symbol, th Thresholds) []store.Violation {
	bySuffix := map[string][]string{} // suffix -> []className
	for _, s := range symbols {
		if s.Kind != "class" {
			continue
		}
		for _, suf := range NamingNoise {
			if strings.HasSuffix(s.Name, suf) {
				bySuffix[suf] = append(bySuffix[suf], s.Name)
				break
			}
		}
	}
	var out []store.Violation
	for suf, names := range bySuffix {
		if len(names) < th.NoiseSameSuffix {
			continue
		}
		out = append(out, store.Violation{
			ScanID:   scanID,
			Kind:     "overeng",
			Src:      "naming-noise:" + suf,
			Severity: "info",
			Detail: fmt.Sprintf("以 %s 结尾的类有 %d 个（阈值 %d），考虑用业务领域名重命名：%s",
				suf, len(names), th.NoiseSameSuffix, joinTrunc(names, 6)),
		})
	}
	return out
}

// detectAbstractWithoutImpl 找：interface 或抽象类（kind=interface）
// 在 inherit 类型边里被「指向」次数 < MinAbstractCallers 的 case。
//
// 注意：archd 当前 Symbol.Kind 在 Java 里能区分 interface / class；
// abstract class 在 Java 文件里仍登记为 class（modifiers 没有进 symbols），
// 此处保守只覆盖 interface。
func detectAbstractWithoutImpl(scanID int64, symbols []store.Symbol, edges []store.Edge, th Thresholds) []store.Violation {
	implRefCount := map[string]int{}
	for _, e := range edges {
		if e.Kind != "inherit" {
			continue
		}
		implRefCount[e.Dst]++
		// 也按短名（最后一段）登记一次，正则解析阶段父类常被记成短名
		if i := strings.LastIndex(e.Dst, "."); i > 0 {
			implRefCount[e.Dst[i+1:]]++
		}
	}
	var out []store.Violation
	for _, s := range symbols {
		if s.Kind != "interface" {
			continue
		}
		c := implRefCount[s.Name]
		if c >= th.MinAbstractCallers {
			continue
		}
		out = append(out, store.Violation{
			ScanID:   scanID,
			Kind:     "overeng",
			Src:      fmt.Sprintf("%s::%s", s.FilePath, s.Name),
			Severity: "info",
			Detail: fmt.Sprintf("interface %s 仅被 %d 个类型引用（阈值 %d），考虑去抽象，直接使用具体类",
				s.Name, c, th.MinAbstractCallers),
		})
	}
	return out
}

// detectDeepInheritance 给单类型多于 MaxParents 个父类的写一条 hint。
//
// edges 里 kind=inherit 的 src 是子类的 moduleID，
// 没有「子类符号 → 父类符号」直接连，所以这里改用 symbols 中的 Parent 字段
// 是不行的（parent 表示嵌套类，不是继承）。退化做法：
//   - 如果一个文件里同一行声明附近 inherit 边数量很多，则触发。
//
// 由于 edges 没有源行号，我们简化为：按 src moduleID 统计 inherit 边数量。
func detectDeepInheritance(scanID int64, symbols []store.Symbol, edges []store.Edge, th Thresholds) []store.Violation {
	inheritBySrc := map[string]int{}
	for _, e := range edges {
		if e.Kind != "inherit" {
			continue
		}
		inheritBySrc[e.Src]++
	}
	var out []store.Violation
	for src, n := range inheritBySrc {
		if n < th.MaxParents+1 {
			continue
		}
		out = append(out, store.Violation{
			ScanID:   scanID,
			Kind:     "overeng",
			Src:      src,
			Severity: "warning",
			Detail: fmt.Sprintf("模块 %s 累计声明 %d 条父类/接口继承，多于阈值 %d，考虑使用组合或拆类",
				src, n, th.MaxParents),
		})
	}
	_ = symbols
	return out
}

// joinTrunc 把一个字符串切片用逗号连接，超过 max 用 «..» 截断。
func joinTrunc(s []string, max int) string {
	if len(s) <= max {
		return strings.Join(s, ", ")
	}
	return strings.Join(s[:max], ", ") + fmt.Sprintf(", … (+%d)", len(s)-max)
}
