// Package api 提供 codeguard-archd 的 HTTP 入口。
//
// 路由树（前缀均为 /api/arch）：
//
//	GET    /health              健康检查
//	POST   /scan/:scan_id       触发或重跑某次扫描
//	GET    /scan/:scan_id       查询某次扫描的状态摘要
//	GET    /graph/:scan_id      模块依赖图（节点 + 边）
//	GET    /cycles/:scan_id     循环依赖列表
//	GET    /violations/:scan_id 架构违规列表（layer / godclass / overeng / longmethod）
//	GET    /patterns/:scan_id   模式识别列表
//	GET    /hotspots/:scan_id   热点（健康度倒序）
//	GET    /radar/:scan_id      6 维雷达 + overall
//	GET    /treemap/:scan_id    模块体积树状结构（已聚合）
//	GET    /symbols/:scan_id    符号清单（按文件分组）
//
// 全部 GET 都是只读，幂等；POST /scan/:scan_id 是幂等的「重置 + 重跑」。
package api

import (
	"net/http"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/jmoiron/sqlx"
)

// NewRouter 装配 Gin 引擎；在 main.go 里直接调用并 Run。
//
// 默认中间件：Logger + Recovery + 宽松 CORS（allow all origins）。
// 课程项目部署单机，CORS 不做收紧；生产化再按域白名单切换。
func NewRouter(db *sqlx.DB) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Logger(), gin.Recovery())
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		AllowCredentials: false,
		MaxAge:           5 * time.Minute,
	}))

	h := newHandlers(db)
	g := r.Group("/api/arch")
	{
		g.GET("/health", h.health)
		g.POST("/scan/:scan_id", h.runScan)
		g.GET("/scan/:scan_id", h.scanStatus)
		g.GET("/graph/:scan_id", h.graph)
		g.GET("/cycles/:scan_id", h.cycles)
		g.GET("/violations/:scan_id", h.violations)
		g.GET("/patterns/:scan_id", h.patterns)
		g.GET("/hotspots/:scan_id", h.hotspots)
		g.GET("/radar/:scan_id", h.radar)
		g.GET("/treemap/:scan_id", h.treemap)
		g.GET("/symbols/:scan_id", h.symbols)
	}

	// 兜底 404，让 Python 端聚合层能稳定识别。
	r.NoRoute(func(c *gin.Context) {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found", "path": c.Request.URL.Path})
	})
	return r
}
