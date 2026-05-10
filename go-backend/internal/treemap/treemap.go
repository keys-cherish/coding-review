// Package treemap 把模块列表聚合为「目录 → 文件」层级结构，
// 形状对齐前端 ECharts treemap / sunburst data 字段（name + value + children + colorValue）。
//
// 设计要点：
//
//   1. 只输出 JSON 友好的纯 map[string]any，避免类型与前端协议耦合；
//   2. value = 模块 LOC，叶子节点直接取自 modules；中间节点累加；
//   3. colorValue = 模块的 fan_in*fan_out（耦合代理），中间节点取最大值，
//      让 treemap 的颜色映射可以反映「热点路径」；
//   4. 路径分隔符以正斜杠 / 为准（解析阶段已规范化）。
package treemap

import (
	"sort"
	"strings"

	"codeguard/archd/internal/store"
)

// Build 返回根节点（name="root"），调用方按需取 children。
func Build(modules []store.Module) map[string]any {
	root := map[string]any{
		"name":     "root",
		"value":    0,
		"children": []any{},
	}
	for _, m := range modules {
		insert(root, splitPath(m.FilePath), m)
	}
	finalize(root)
	return root
}

// splitPath 把相对路径切成段，过滤掉空段。
func splitPath(p string) []string {
	p = strings.ReplaceAll(p, "\\", "/")
	parts := strings.Split(p, "/")
	out := parts[:0]
	for _, s := range parts {
		if s != "" {
			out = append(out, s)
		}
	}
	return out
}

// insert 把一个模块沿路径下放到树中，自动创建中间节点。
func insert(node map[string]any, path []string, m store.Module) {
	cur := node
	for i, seg := range path {
		isLeaf := i == len(path)-1
		children := cur["children"].([]any)
		var child map[string]any
		for _, c := range children {
			cm := c.(map[string]any)
			if cm["name"].(string) == seg {
				child = cm
				break
			}
		}
		if child == nil {
			child = map[string]any{
				"name":     seg,
				"value":    0,
				"children": []any{},
			}
			children = append(children, child)
			cur["children"] = children
		}
		if isLeaf {
			child["value"] = m.LOC
			child["module_id"] = m.ModuleID
			child["language"] = m.Language
			child["fan_in"] = m.FanIn
			child["fan_out"] = m.FanOut
			child["layer"] = m.Layer
			// colorValue 用 fan_in*fan_out 作为「耦合度」代理
			child["colorValue"] = m.FanIn * m.FanOut
		}
		cur = child
	}
}

// finalize 自底向上把中间节点的 value 与 colorValue 聚合好。
//
// 同时：移除完全没有 children 的中间空节点（防御性写法，正常路径不会出现）。
// 对每层 children 按 value 降序排，便于前端默认布局漂亮。
func finalize(node map[string]any) (int, int) {
	children := node["children"].([]any)
	if len(children) == 0 {
		v, _ := node["value"].(int)
		c, _ := node["colorValue"].(int)
		return v, c
	}
	totalV := 0
	maxC := 0
	for _, c := range children {
		cm := c.(map[string]any)
		v, color := finalize(cm)
		totalV += v
		if color > maxC {
			maxC = color
		}
	}
	if existing, ok := node["value"].(int); ok && existing > 0 {
		// 叶子节点已被赋值，保持不变（应该不会进 finalize 这里）
		_ = existing
	}
	node["value"] = totalV
	if _, has := node["colorValue"]; !has {
		node["colorValue"] = maxC
	}
	sort.SliceStable(children, func(i, j int) bool {
		ci := children[i].(map[string]any)
		cj := children[j].(map[string]any)
		return toInt(ci["value"]) > toInt(cj["value"])
	})
	node["children"] = children
	return totalV, maxC
}

func toInt(v any) int {
	if v == nil {
		return 0
	}
	if i, ok := v.(int); ok {
		return i
	}
	return 0
}
