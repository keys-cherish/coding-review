// Package main 启动 codeguard-archd (Architecture Daemon)。
//
// 设计定位
// --------
// archd 是 CodeGuard Pro 的「结构性分析守护进程」，由 Go 编写，
// 利用 Tree-sitter CGo 绑定在毫秒级完成跨文件图结构分析。
//
// 它不取代 Python FastAPI 的业务编排能力，只承担大模型和纯 Python
// 都无法胜任的任务：
//   - 十万行代码级别的调用图 / 依赖图 / 继承图
//   - Tarjan SCC 等图算法
//   - 架构模式指纹匹配
//   - UML / ER 图生成
//
// 对外以 REST JSON 暴露 /api/arch/*，由前端或 Python 聚合层调用。
package main

import (
	"log"
	"os"

	"codeguard/archd/internal/api"
	"codeguard/archd/internal/store"
)

func main() {
	dbPath := os.Getenv("CODEGUARD_DB")
	if dbPath == "" {
		// 默认指向项目根目录下 data/codeguard.db
		dbPath = "../data/codeguard.db"
	}

	addr := os.Getenv("ARCHD_ADDR")
	if addr == "" {
		addr = ":8001"
	}

	db, err := store.Open(dbPath)
	if err != nil {
		log.Fatalf("open sqlite: %v", err)
	}
	defer db.Close()

	// 建表（幂等）
	if err := store.Migrate(db); err != nil {
		log.Fatalf("migrate: %v", err)
	}

	router := api.NewRouter(db)
	log.Printf("codeguard-archd listening on %s (db=%s)", addr, dbPath)
	if err := router.Run(addr); err != nil {
		log.Fatalf("gin run: %v", err)
	}
}
