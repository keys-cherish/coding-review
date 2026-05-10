// Package layer 推断分层并检测「单向依赖」违规。
//
// 推断策略：
//
//   按 moduleID 中包含的「关键词片段」给每个模块打层标签。
//   关键词列表是硬编码常识（routers/controllers, services, engines, models, utils）。
//   未匹配的模块标签为空字符串，参与统计但不参与违规计算。
//
// 违规判定：
//
//   每个 layer 有一个 rank（数字越小越高层）。当一条边 src->dst 的
//   src.rank < dst.rank（高层调用低层）：合规；
//   src.rank > dst.rank（低层反向调用高层）：violation severity=error；
//   src.rank == dst.rank 但模块前缀不同：跨同层违规 severity=warning。
package layer

import (
	"fmt"
	"strings"

	"codeguard/archd/internal/store"
)

// Definition 定义了一层及其匹配关键词、rank。
type Definition struct {
	Name     string
	Rank     int      // 数字越小越「上层」
	Keywords []string // 模块 ID 中包含任一关键词即归类
}

// DefaultLayers 是适合 FastAPI / Spring / Layered Web 项目的默认分层。
// 顺序很重要：Detect 自上而下匹配，遇到第一个就停。
var DefaultLayers = []Definition{
	{Name: "presentation", Rank: 1, Keywords: []string{".routers.", ".controller.", ".controllers.", ".api.", ".views.", ".web.", "/routers/", "/controllers/"}},
	{Name: "application", Rank: 2, Keywords: []string{".services.", ".usecase.", ".usecases.", "/services/"}},
	{Name: "domain", Rank: 3, Keywords: []string{".engines.", ".domain.", ".core.", "/engines/", "/domain/"}},
	{Name: "data", Rank: 4, Keywords: []string{".models.", ".entities.", ".repository.", ".repositories.", ".dao.", "/models/", "/repository/"}},
	{Name: "infra", Rank: 5, Keywords: []string{".utils.", ".helpers.", ".common.", ".database.", ".config.", "/utils/", "/common/"}},
}

// LayerOf 把单个 moduleID 分类到 DefaultLayers 之一。
//
// 匹配时同时尝试 dotted 形式（".routers."）与 slash 形式（"/routers/"），
// 因为模块 ID 通常是 dotted，但有些项目 ID 是 slash 路径。
func LayerOf(moduleID string) (string, int) {
	id := moduleID
	if !strings.Contains(id, ".") {
		// 没有 dot 时给两端加 dot 让 ".x." 关键词命中
		id = "." + id + "."
	} else {
		id = "." + id + "."
	}
	for _, d := range DefaultLayers {
		for _, kw := range d.Keywords {
			if strings.Contains(id, kw) {
				return d.Name, d.Rank
			}
		}
	}
	return "", 0
}

// AssignLayers 给每个模块写入 layer 字段，返回 (moduleID -> layerName)。
// 这个 map 由编排层 store.UpdateModuleLayer 落库。
func AssignLayers(modules []store.Module) map[string]string {
	out := map[string]string{}
	for _, m := range modules {
		name, _ := LayerOf(m.ModuleID)
		out[m.ModuleID] = name
	}
	return out
}

// DetectViolations 走每条 import/inherit 边，按 rank 比较出违规。
//
// 仅检查双方都已分层（rank > 0）的边；任何一方未分层都跳过，
// 避免把 utils ↔ utils 这类「共享层内部」误报。
func DetectViolations(scanID int64, edges []store.Edge) []store.Violation {
	var out []store.Violation
	for _, e := range edges {
		if e.Kind != "import" {
			continue
		}
		sn, sr := LayerOf(e.Src)
		dn, dr := LayerOf(e.Dst)
		if sr == 0 || dr == 0 {
			continue
		}
		if sr > dr {
			out = append(out, store.Violation{
				ScanID:   scanID,
				Kind:     "layer",
				Src:      e.Src,
				Dst:      e.Dst,
				Severity: "error",
				Detail: fmt.Sprintf("分层倒置：%s（layer=%s rank=%d）依赖了 %s（layer=%s rank=%d）",
					e.Src, sn, sr, e.Dst, dn, dr),
			})
		}
	}
	return out
}

