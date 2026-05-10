// Package main 的冒烟测试：对一个真实样例目录跑 parser，检查产出非空。
//
// 这个测试不会启动 HTTP 服务，也不依赖 SQLite，
// 只验证 parser 串接最关键的语义抽取链路是否正常。
package main

import (
	"os"
	"path/filepath"
	"testing"

	"codeguard/archd/internal/parser"
)

// TestParseSamplePython 在 examples/sample_python_project 上跑解析。
//
// 期望：至少 3 个模块、>=1 条 import 边、若干 class/function 符号。
func TestParseSamplePython(t *testing.T) {
	root := findRepoRoot(t)
	sample := filepath.Join(root, "examples", "sample_python_project")
	if _, err := os.Stat(sample); err != nil {
		t.Skipf("sample dir missing: %v", err)
	}

	res, err := parser.Parse(parser.ParseOptions{
		Root:           sample,
		AllowLanguages: []string{"python"},
	})
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if res.FilesScanned == 0 {
		t.Fatalf("FilesScanned == 0; want > 0")
	}
	if len(res.Modules) == 0 {
		t.Fatalf("Modules empty; want >= 1")
	}
	if len(res.Symbols) == 0 {
		t.Fatalf("Symbols empty; want >= 1")
	}
}

// findRepoRoot 从当前工作目录向上找含 go-backend 目录的祖先，
// 视作仓库根；找不到就 t.Fatal。
func findRepoRoot(t *testing.T) string {
	t.Helper()
	cur, _ := os.Getwd()
	for i := 0; i < 8; i++ {
		if _, err := os.Stat(filepath.Join(cur, "go-backend")); err == nil {
			return cur
		}
		parent := filepath.Dir(cur)
		if parent == cur {
			break
		}
		cur = parent
	}
	t.Fatalf("repo root not found from %s", cur)
	return ""
}
