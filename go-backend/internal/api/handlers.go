// Package api 中：所有 HTTP handler。
//
// 设计风格：
//   - 每个 handler 只做「参数解析 → store 查询 → 整形输出」三步；
//   - 复杂业务（扫描编排）放在 scan.go；
//   - JSON 字段名统一 snake_case，与 Python 端风格一致。
package api

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jmoiron/sqlx"

	"codeguard/archd/internal/radar"
	"codeguard/archd/internal/store"
	"codeguard/archd/internal/treemap"
)

// handlers 把 db 注入到所有 endpoint，避免每个函数闭包散落 db 引用。
type handlers struct {
	db *sqlx.DB
}

func newHandlers(db *sqlx.DB) *handlers {
	return &handlers{db: db}
}

// parseScanID 提取并校验 :scan_id；失败时直接渲染 400。
func parseScanID(c *gin.Context) (int64, bool) {
	raw := c.Param("scan_id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id <= 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid scan_id", "value": raw})
		return 0, false
	}
	return id, true
}

func (h *handlers) health(c *gin.Context) {
	// SQLite Ping 确认数据库可用，避免「服务进程在但数据库挂了」假阳性
	dbOK := true
	if err := h.db.Ping(); err != nil {
		dbOK = false
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  "ok",
		"db":      dbOK,
		"service": "codeguard-archd",
		"version": "0.1.0",
	})
}

// runScan 触发一次完整扫描（同步）。
// 客户端可以用 fetch + 长 timeout 等待；典型耗时 < 3s。
func (h *handlers) runScan(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	report, err := RunScan(h.db, scanID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "scan failed",
			"detail":  err.Error(),
			"scan_id": scanID,
		})
		return
	}
	c.JSON(http.StatusOK, report)
}

// scanStatus 给前端确认「这次扫描是否已经被 archd 处理过」。
func (h *handlers) scanStatus(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	mods, err := store.LoadModules(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	rad, _ := store.LoadRadar(h.db, scanID)
	cycles, _ := store.LoadCycles(h.db, scanID)
	violations, _ := store.LoadViolations(h.db, scanID)

	resp := gin.H{
		"scan_id":          scanID,
		"modules":          len(mods),
		"cycles":           len(cycles),
		"violations":       len(violations),
		"has_radar":        rad != nil,
		"already_analyzed": len(mods) > 0,
	}
	if rad != nil {
		resp["overall"] = radar.Overall(*rad)
		resp["radar"] = rad
	}
	c.JSON(http.StatusOK, resp)
}

// graph 输出依赖图：节点 + 边 + 类目。
//
// 字段对齐 frontend/src/views/Graph.ts 的 DepGraphPayload，
// 让前端无需再做字段映射。
func (h *handlers) graph(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	mods, err := store.LoadModules(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	edges, err := store.LoadEdges(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	cycles, _ := store.LoadCycles(h.db, scanID)

	// 哪些模块在循环里
	inCycle := map[string]bool{}
	for _, cyc := range cycles {
		var ids []string
		_ = json.Unmarshal([]byte(cyc.ModulesJSON), &ids)
		for _, id := range ids {
			inCycle[id] = true
		}
	}

	// 节点：把顶级目录段当作 category
	categoryByName := map[string]int{}
	var categories []gin.H
	type nodeOut struct {
		ID        string `json:"id"`
		Name      string `json:"name"`
		FilePath  string `json:"file_path"`
		LOC       int    `json:"loc"`
		FanIn     int    `json:"fan_in"`
		FanOut    int    `json:"fan_out"`
		Size      int    `json:"size"`
		Category  int    `json:"category"`
		InCycle   bool   `json:"in_cycle"`
		Layer     string `json:"layer"`
	}
	nodes := make([]nodeOut, 0, len(mods))
	for _, m := range mods {
		cat := topCategory(m.FilePath)
		idx, hasIdx := categoryByName[cat]
		if !hasIdx {
			idx = len(categories)
			categoryByName[cat] = idx
			categories = append(categories, gin.H{"name": cat})
		}
		size := 12 + intSqrt(m.LOC)
		if size > 60 {
			size = 60
		}
		nodes = append(nodes, nodeOut{
			ID:       m.ModuleID,
			Name:     shortName(m.ModuleID),
			FilePath: m.FilePath,
			LOC:      m.LOC,
			FanIn:    m.FanIn,
			FanOut:   m.FanOut,
			Size:     size,
			Category: idx,
			InCycle:  inCycle[m.ModuleID],
			Layer:    m.Layer,
		})
	}

	type linkOut struct {
		Source string `json:"source"`
		Target string `json:"target"`
		Value  int    `json:"value"`
		Kind   string `json:"kind"`
	}
	links := make([]linkOut, 0, len(edges))
	for _, e := range edges {
		links = append(links, linkOut{
			Source: e.Src,
			Target: e.Dst,
			Value:  e.Count,
			Kind:   e.Kind,
		})
	}

	// 简单 stats
	totFanIn, totFanOut := 0, 0
	for _, m := range mods {
		totFanIn += m.FanIn
		totFanOut += m.FanOut
	}
	stats := gin.H{}
	if len(mods) > 0 {
		stats["avg_fan_in"] = float64(totFanIn) / float64(len(mods))
		stats["avg_fan_out"] = float64(totFanOut) / float64(len(mods))
	}

	// 把 cycle 转成前端期望的 DepCycle 形状
	type depCycle struct {
		Size           int      `json:"size"`
		Severity       string   `json:"severity"`
		Description    string   `json:"description"`
		ShortestCycle  []string `json:"shortest_cycle"`
		Modules        []string `json:"modules"`
	}
	dcycles := make([]depCycle, 0, len(cycles))
	for _, cy := range cycles {
		var members []string
		_ = json.Unmarshal([]byte(cy.ModulesJSON), &members)
		var path []string
		_ = json.Unmarshal([]byte(cy.PathJSON), &path)
		dcycles = append(dcycles, depCycle{
			Size:          cy.Size,
			Severity:      cy.Severity,
			Description:   cycleDesc(cy.Severity, cy.Size),
			ShortestCycle: path,
			Modules:       members,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"nodes":      nodes,
		"links":      links,
		"categories": categories,
		"cycles":     dcycles,
		"stats":      stats,
	})
}

// cycles 仅返回循环依赖（不含图结构）。
func (h *handlers) cycles(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	rows, err := store.LoadCycles(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	type out struct {
		Size     int      `json:"size"`
		Severity string   `json:"severity"`
		Modules  []string `json:"modules"`
		Path     []string `json:"path"`
	}
	list := make([]out, 0, len(rows))
	for _, r := range rows {
		var members, path []string
		_ = json.Unmarshal([]byte(r.ModulesJSON), &members)
		_ = json.Unmarshal([]byte(r.PathJSON), &path)
		list = append(list, out{Size: r.Size, Severity: r.Severity, Modules: members, Path: path})
	}
	c.JSON(http.StatusOK, gin.H{"cycles": list, "total": len(list)})
}

func (h *handlers) violations(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	rows, err := store.LoadViolations(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	byKind := map[string]int{}
	for _, r := range rows {
		byKind[r.Kind]++
	}
	c.JSON(http.StatusOK, gin.H{
		"violations": rows,
		"total":      len(rows),
		"by_kind":    byKind,
	})
}

func (h *handlers) patterns(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	rows, err := store.LoadPatterns(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	primary := ""
	for _, r := range rows {
		// 选第一个 confidence > 0.7 的当 primary
		if r.Confidence > 0.7 {
			primary = r.Pattern
			break
		}
	}
	c.JSON(http.StatusOK, gin.H{
		"patterns": rows,
		"total":    len(rows),
		"primary":  primary,
	})
}

func (h *handlers) hotspots(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	rows, err := store.LoadHotspots(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	c.JSON(http.StatusOK, gin.H{"hotspots": rows, "total": len(rows)})
}

func (h *handlers) radar(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	r, err := store.LoadRadar(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	if r == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "no radar for scan", "scan_id": scanID})
		return
	}

	// 6 个维度；与前端 RadarPayload 对齐
	dims := []gin.H{
		{"name": "清晰度", "score": r.Clarity, "detail": "分层覆盖比例（layer 非空模块）"},
		{"name": "隔离度", "score": r.Isolation, "detail": "分层违规越少越高分"},
		{"name": "解耦度", "score": r.Decoupling, "detail": "fan_out 平均与循环依赖数双因子"},
		{"name": "内聚度", "score": r.Cohesion, "detail": "godclass / longmethod 反向计分"},
		{"name": "规范度", "score": r.Discipline, "detail": "过度设计违规反向计分"},
		{"name": "规整度", "score": r.Redundancy, "detail": "平均路径深度与最大深度反向计分"},
	}
	overall := radar.Overall(*r)
	grade := "D"
	switch {
	case overall >= 90:
		grade = "A"
	case overall >= 75:
		grade = "B"
	case overall >= 60:
		grade = "C"
	}
	c.JSON(http.StatusOK, gin.H{
		"dimensions": dims,
		"overall":    overall,
		"grade":      grade,
		"scan_id":    scanID,
	})
}

func (h *handlers) treemap(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	mods, err := store.LoadModules(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	tree := treemap.Build(mods)
	c.JSON(http.StatusOK, tree)
}

func (h *handlers) symbols(c *gin.Context) {
	scanID, ok := parseScanID(c)
	if !ok {
		return
	}
	rows, err := store.LoadSymbols(h.db, scanID)
	if err != nil {
		dbErr(c, err)
		return
	}
	byKind := map[string]int{}
	for _, r := range rows {
		byKind[r.Kind]++
	}
	c.JSON(http.StatusOK, gin.H{"symbols": rows, "total": len(rows), "by_kind": byKind})
}

// dbErr 是数据库错误的统一渲染。
func dbErr(c *gin.Context, err error) {
	c.JSON(http.StatusInternalServerError, gin.H{
		"error":  "db query failed",
		"detail": err.Error(),
	})
}

// shortName 把 a.b.c 缩成 c；用于图节点 label。
func shortName(mid string) string {
	for i := len(mid) - 1; i >= 0; i-- {
		if mid[i] == '.' {
			return mid[i+1:]
		}
	}
	return mid
}

// topCategory 取相对路径首段作为 category 名（categoryByName 的稳定 key）。
func topCategory(filePath string) string {
	for i, c := range filePath {
		if c == '/' || c == '\\' {
			return filePath[:i]
		}
	}
	return filePath
}

// intSqrt 整数开方近似（避免 math.Sqrt 引入浮点）。给节点尺寸用。
func intSqrt(n int) int {
	if n <= 1 {
		return n
	}
	x := n
	y := (x + 1) / 2
	for y < x {
		x = y
		y = (x + n/x) / 2
	}
	return x
}

// cycleDesc 给前端展示的「人类可读描述」。
func cycleDesc(severity string, size int) string {
	switch severity {
	case "critical":
		return "高严重度循环：可能含通配 import 或大型 SCC，建议优先打断"
	case "major":
		return "中严重度循环：3~5 个模块互相依赖，需要重构"
	case "minor":
		return "低严重度循环：双向耦合，常可通过抽接口分离"
	default:
		_ = size
		return "循环依赖"
	}
}
