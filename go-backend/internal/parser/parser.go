// Package parser 提供 Python / Java 源文件的轻量级结构提取。
//
// 设计取舍
// --------
// 没有走 tree-sitter / CGo 路线，原因有三：
//  1. archd 关心的是「跨文件级」结构（import/继承/调用），
//     单文件级 AST 精度交给 Python 端 ast 模块即可；
//  2. tree-sitter CGo 在 Windows 上构建链路敏感，回归 stdlib 减少跨平台风险；
//  3. import / class / def / method 这些声明本身是相当规则的语法，
//     用「正则 + 行级状态机」就足够稳健。
//
// 结果以 ParseResult 暴露，下游分析模块全部消费同一中间表示。
package parser

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"codeguard/archd/internal/store"
)

// ParseResult 是一次目录扫描的全部产物。
//
// 它故意不携带任何 ScanID 字段——ScanID 是落库职责，由编排层
// 在批量写入时统一注入；这样 parser 包就能在测试里独立运行。
type ParseResult struct {
	Modules []store.Module
	Edges   []store.Edge
	Symbols []store.Symbol
	Calls   []store.Call
	VarRefs []store.VarRef

	// FilesScanned 与 FilesSkipped 用于 API 给前端进度指标。
	FilesScanned int
	FilesSkipped int
}

// ParseOptions 控制本次扫描的范围与归属语言。
type ParseOptions struct {
	// Root 是源码根目录，所有路径都以此为基准计算相对路径。
	Root string

	// AllowLanguages 限定扫描的语言；空表示默认扫 python+java。
	AllowLanguages []string

	// ScanID 仅用于在结果上打标签（落库时使用），parser 自身不读它。
	ScanID int64

	// MaxBytes 单文件大小上限，超过则跳过（避免读入巨型生成物）。
	// 0 表示不限制；默认 2 MiB。
	MaxBytes int64
}

// Parse 是包级入口，按 opts.Root 走目录树，对每个支持的源文件做解析。
//
// 跳过规则：
//   - 隐藏目录（.git / .venv / __pycache__ / node_modules / target / build）
//   - 非源代码文件
//   - 体积超过 opts.MaxBytes 的文件
//
// 调用方常见用法：
//
//	res, err := parser.Parse(ctx, parser.ParseOptions{Root: dir, ScanID: id})
func Parse(opts ParseOptions) (*ParseResult, error) {
	if opts.Root == "" {
		return nil, fmt.Errorf("parser.Parse: empty root")
	}
	if opts.MaxBytes == 0 {
		opts.MaxBytes = 2 << 20
	}
	if len(opts.AllowLanguages) == 0 {
		opts.AllowLanguages = []string{"python", "java"}
	}
	allow := map[string]bool{}
	for _, l := range opts.AllowLanguages {
		allow[l] = true
	}

	res := &ParseResult{}

	// 第一遍：收集所有源文件 + 构建 module_id 映射。
	type fileTask struct {
		absPath  string
		relPath  string
		language string
	}
	var files []fileTask
	moduleIDs := map[string]string{} // relPath -> moduleID

	err := filepath.Walk(opts.Root, func(p string, info os.FileInfo, walkErr error) error {
		if walkErr != nil {
			return nil // 走不动的子树静默跳过，不阻塞整次扫描
		}
		if info == nil {
			return nil
		}
		if info.IsDir() {
			if isSkippableDir(info.Name()) {
				return filepath.SkipDir
			}
			return nil
		}
		lang := languageOf(p)
		if lang == "" || !allow[lang] {
			return nil
		}
		if info.Size() > opts.MaxBytes {
			res.FilesSkipped++
			return nil
		}
		rel, err := filepath.Rel(opts.Root, p)
		if err != nil {
			return nil
		}
		rel = filepath.ToSlash(rel)
		mid := makeModuleID(rel, lang)
		moduleIDs[rel] = mid
		files = append(files, fileTask{absPath: p, relPath: rel, language: lang})
		return nil
	})
	if err != nil {
		return nil, fmt.Errorf("walk root: %w", err)
	}

	// 第二遍：解析每个文件，把 Edge 的目标先用「字符串目标名」存放，
	// 全部解析完后再做一次「目标名 → moduleID」的解析（resolve）。
	relPathByModuleSuffix := buildSuffixIndex(moduleIDs)

	for _, f := range files {
		text, err := readBounded(f.absPath, opts.MaxBytes)
		if err != nil {
			res.FilesSkipped++
			continue
		}
		var fileRes *fileResult
		switch f.language {
		case "python":
			fileRes = parsePython(text, f.relPath)
		case "java":
			fileRes = parseJava(text, f.relPath)
		default:
			continue
		}

		mid := moduleIDs[f.relPath]
		mod := store.Module{
			ScanID:   opts.ScanID,
			ModuleID: mid,
			FilePath: f.relPath,
			Language: f.language,
			LOC:      fileRes.loc,
		}
		res.Modules = append(res.Modules, mod)
		res.FilesScanned++

		for _, sym := range fileRes.symbols {
			sym.ScanID = opts.ScanID
			sym.FilePath = f.relPath
			res.Symbols = append(res.Symbols, sym)
		}
		for _, c := range fileRes.calls {
			c.ScanID = opts.ScanID
			c.FilePath = f.relPath
			res.Calls = append(res.Calls, c)
		}
		for _, vr := range fileRes.varRefs {
			vr.ScanID = opts.ScanID
			vr.FilePath = f.relPath
			res.VarRefs = append(res.VarRefs, vr)
		}

		for _, raw := range fileRes.rawImports {
			dst := resolveImportTarget(raw.target, mid, relPathByModuleSuffix)
			if dst == "" || dst == mid {
				continue
			}
			res.Edges = append(res.Edges, store.Edge{
				ScanID:     opts.ScanID,
				Src:        mid,
				Dst:        dst,
				Kind:       raw.kind,
				Count:      1,
				IsWildcard: boolToInt(raw.isWildcard),
			})
		}
	}

	return res, nil
}

// fileResult 只在 parser 包内部使用，把单文件解析结果汇总后再
// 与全局 moduleID 表做最终拼装。
type fileResult struct {
	loc        int
	symbols    []store.Symbol
	calls      []store.Call
	varRefs    []store.VarRef
	rawImports []rawImport
}

// rawImport 是「我引用了某个名字 X」的记录，
// resolve 阶段才决定它对应哪一个本项目 moduleID。
type rawImport struct {
	target     string // python: pkg.mod 或 .relative.mod；java: a.b.C
	kind       string // import / inherit
	isWildcard bool
}

// languageOf 用扩展名判别语言。其他扩展（.go/.ts/.cpp）暂不解析。
func languageOf(p string) string {
	ext := strings.ToLower(filepath.Ext(p))
	switch ext {
	case ".py":
		return "python"
	case ".java":
		return "java"
	}
	return ""
}

// isSkippableDir 是从工程经验里挑出的常见生成物 / 隔离目录。
func isSkippableDir(name string) bool {
	switch name {
	case ".git", ".hg", ".svn",
		".venv", "venv", "env",
		"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
		"node_modules", "bower_components",
		"target", "build", "dist", "out",
		".idea", ".vscode":
		return true
	}
	// 以 . 起头的隐藏目录默认跳过，但保留 .github 之类的常见配置目录意义不大
	if strings.HasPrefix(name, ".") {
		return true
	}
	return false
}

// readBounded 读取一个体积可控的文件；超过上限直接 fail-fast。
func readBounded(path string, max int64) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	if int64(len(data)) > max {
		return "", fmt.Errorf("file too large")
	}
	return string(data), nil
}

// makeModuleID 把相对路径变成跨语言一致的 moduleID。
//
// Python: backend/engines/parser/__init__.py → backend.engines.parser
//	       backend/engines/parser/python.py    → backend.engines.parser.python
// Java:   src/main/java/com/foo/Bar.java     → com.foo.Bar
//
// Java 路径里识别 src/{main,test}/java 段并截断（这是 Maven/Gradle 的惯例）。
func makeModuleID(relPath, language string) string {
	rel := strings.TrimSuffix(relPath, filepath.Ext(relPath))
	rel = filepath.ToSlash(rel)
	parts := strings.Split(rel, "/")

	if language == "java" {
		// 找到 src/(main|test)/java 段后保留其后的部分
		for i := 0; i < len(parts)-2; i++ {
			if parts[i] == "src" && (parts[i+1] == "main" || parts[i+1] == "test") && parts[i+2] == "java" {
				parts = parts[i+3:]
				break
			}
		}
		return strings.Join(parts, ".")
	}

	// Python: __init__ 等价于该目录本身
	if len(parts) > 0 && parts[len(parts)-1] == "__init__" {
		parts = parts[:len(parts)-1]
	}
	return strings.Join(parts, ".")
}

// buildSuffixIndex 用模块 ID 的「后缀片段」做反查：
// 给一个 import 名 a.b.c，能从中找出 ID 以 a.b.c 结尾的本地模块。
//
// 数据结构：suffix -> []moduleID。某些 suffix 可能命中多个候选，
// 取最具体的（segments 最多）作为 winner。
func buildSuffixIndex(moduleIDs map[string]string) map[string][]string {
	index := map[string][]string{}
	for _, mid := range moduleIDs {
		segs := strings.Split(mid, ".")
		for i := range segs {
			suf := strings.Join(segs[i:], ".")
			index[suf] = append(index[suf], mid)
		}
	}
	return index
}

// resolveImportTarget 把字符串目标解析为本地 moduleID；解析不到返回 ""，
// 调用方自己决定跳过这条「外部依赖」。
//
// 处理规则：
//  1. 优先精确匹配；
//  2. Python 相对导入（以 . 开头），按当前 srcModuleID 的前缀拼接后再走精确匹配；
//  3. 否则用后缀索引找最具体的命中。
func resolveImportTarget(target, srcMID string, index map[string][]string) string {
	if target == "" {
		return ""
	}
	if strings.HasPrefix(target, ".") {
		// 相对导入：把 . 数量减一作为「向上回退几层」
		nDots := 0
		for _, c := range target {
			if c == '.' {
				nDots++
			} else {
				break
			}
		}
		base := strings.Split(srcMID, ".")
		// import . => 当前包；import .. => 上一级
		levels := nDots - 1
		if levels < 0 {
			levels = 0
		}
		if levels > len(base) {
			return ""
		}
		base = base[:len(base)-levels]
		rest := strings.TrimLeft(target, ".")
		if rest != "" {
			base = append(base, strings.Split(rest, ".")...)
		}
		joined := strings.Join(base, ".")
		if cands, ok := index[joined]; ok && len(cands) > 0 {
			return mostSpecific(cands)
		}
		// 相对导入未命中，宁可静默丢弃也不要乱配
		return ""
	}

	// 绝对路径：先尝试整体后缀
	if cands, ok := index[target]; ok {
		return mostSpecific(cands)
	}

	// 退化策略：去掉最尾段（可能是符号名）再试一次
	if i := strings.LastIndex(target, "."); i > 0 {
		head := target[:i]
		if cands, ok := index[head]; ok {
			return mostSpecific(cands)
		}
	}
	return ""
}

// mostSpecific 在多个候选 moduleID 里挑「片段最多」的一条，
// 这通常对应业务模块而非父级包。
func mostSpecific(cands []string) string {
	best := cands[0]
	bestScore := strings.Count(best, ".")
	for _, c := range cands[1:] {
		s := strings.Count(c, ".")
		if s > bestScore {
			best = c
			bestScore = s
		}
	}
	return best
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}
