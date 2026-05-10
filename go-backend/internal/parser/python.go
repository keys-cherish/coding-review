// Package parser 中针对 Python 源文件的实现。
//
// 抽取范围（按需求最小集）：
//   - import / from ... import ...：构造模块边
//   - class ...：类符号 + 父类（继承边）
//   - def ...：函数符号；按缩进级别区分顶层函数 / 类方法
//   - 形如 ident(...) 的调用：构造 call 边（不做语义解析，不区分 a.b())
//   - 模块级变量赋值（首列 letter 起头 = 赋值）：var ref 写入
package parser

import (
	"regexp"
	"strings"

	"codeguard/archd/internal/store"
)

var (
	pyImportRe     = regexp.MustCompile(`^\s*import\s+([\w\.]+)(?:\s+as\s+\w+)?(?:\s*,\s*[\w\.]+(?:\s+as\s+\w+)?)*\s*$`)
	pyFromImportRe = regexp.MustCompile(`^\s*from\s+(\.{0,3}[\w\.]*)\s+import\s+(.+)$`)
	pyClassRe      = regexp.MustCompile(`^(\s*)class\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*:`)
	pyDefRe        = regexp.MustCompile(`^(\s*)def\s+([A-Za-z_]\w*)\s*\(`)
	pyAssignRe     = regexp.MustCompile(`^([A-Za-z_]\w*)\s*=\s*[^=]`)
	pyCallRe       = regexp.MustCompile(`([A-Za-z_]\w*)\s*\(`)
	pyKeywordSet   = map[string]struct{}{
		"if": {}, "elif": {}, "else": {}, "for": {}, "while": {}, "with": {}, "in": {},
		"return": {}, "yield": {}, "and": {}, "or": {}, "not": {}, "is": {}, "lambda": {},
		"def": {}, "class": {}, "from": {}, "import": {}, "as": {}, "pass": {}, "raise": {},
		"try": {}, "except": {}, "finally": {}, "True": {}, "False": {}, "None": {},
		"print": {}, "len": {}, "str": {}, "int": {}, "float": {}, "list": {}, "dict": {},
		"set": {}, "tuple": {}, "bool": {}, "type": {}, "isinstance": {}, "issubclass": {},
		"range": {}, "enumerate": {}, "map": {}, "filter": {}, "zip": {}, "sorted": {},
		"open": {}, "input": {}, "super": {}, "self": {}, "cls": {},
	}
)

// classFrame 用于跟踪当前嵌套类，给 def 归属父类。
type classFrame struct {
	name   string
	indent int
}

// parsePython 是 Python 文件级解析器入口。
//
// 实现策略：单遍逐行，维护 indent → 当前所在 class 的浅栈。
// 这种粗粒度足够生成跨文件视角下的图谱；不做表达式级 AST。
func parsePython(text, relPath string) *fileResult {
	r := &fileResult{}
	lines := strings.Split(text, "\n")
	r.loc = countCodeLines(lines, "python")

	stack := []classFrame{}
	currentFunc := ""

	inDocstring := false
	docDelim := ""

	for i, raw := range lines {
		line := stripPyComment(raw)

		// 处理跨行 docstring，避免里面的 def class 被误识别
		if inDocstring {
			if idx := strings.Index(line, docDelim); idx >= 0 {
				inDocstring = false
				line = line[idx+len(docDelim):]
			} else {
				continue
			}
		}
		if d := openingDocstring(line); d != "" {
			rest := line[strings.Index(line, d)+len(d):]
			if !strings.Contains(rest, d) {
				inDocstring = true
				docDelim = d
				continue
			}
		}

		ws := indentOf(line)
		stripped := strings.TrimSpace(line)
		if stripped == "" {
			continue
		}

		// 维护 class 栈：当前缩进 <= 栈顶 indent 时弹出
		for len(stack) > 0 && ws <= stack[len(stack)-1].indent {
			stack = stack[:len(stack)-1]
		}

		// import / from-import
		if m := pyImportRe.FindStringSubmatch(line); m != nil {
			// 单行可能多个 import a, b, c —— 这里只抓第一个；多个的少见且影响有限
			r.rawImports = append(r.rawImports, rawImport{
				target: strings.TrimSpace(m[1]),
				kind:   "import",
			})
			continue
		}
		if m := pyFromImportRe.FindStringSubmatch(line); m != nil {
			base := strings.TrimSpace(m[1])
			right := strings.TrimSpace(m[2])
			if base == "" && strings.HasPrefix(right, ".") {
				base = right
			}
			isWild := right == "*" || strings.Contains(right, ", *")
			if base != "" {
				r.rawImports = append(r.rawImports, rawImport{
					target:     base,
					kind:       "import",
					isWildcard: isWild,
				})
			}
			// 如果是 from pkg import (Sub1, Sub2)：每个名字也作为可能的子模块边
			for _, name := range splitImportItems(right) {
				if name == "*" || name == "" {
					continue
				}
				combined := base
				if base != "" {
					combined = base + "." + name
				} else {
					combined = name
				}
				r.rawImports = append(r.rawImports, rawImport{
					target: combined,
					kind:   "import",
				})
			}
			continue
		}

		// class
		if m := pyClassRe.FindStringSubmatch(line); m != nil {
			classIndent := len(m[1])
			name := m[2]
			parents := m[3]
			parent := ""
			if len(stack) > 0 {
				parent = stack[len(stack)-1].name
			}
			r.symbols = append(r.symbols, store.Symbol{
				Name:   name,
				Kind:   "class",
				Line:   i + 1,
				Parent: parent,
			})
			// 把基类作为 inherit 边
			for _, p := range splitClassParents(parents) {
				if p == "" {
					continue
				}
				r.rawImports = append(r.rawImports, rawImport{
					target: p,
					kind:   "inherit",
				})
			}
			stack = append(stack, classFrame{name: name, indent: classIndent})
			continue
		}

		// def
		if m := pyDefRe.FindStringSubmatch(line); m != nil {
			name := m[2]
			parent := ""
			kind := "function"
			if len(stack) > 0 {
				parent = stack[len(stack)-1].name
				kind = "method"
			}
			r.symbols = append(r.symbols, store.Symbol{
				Name:   name,
				Kind:   kind,
				Line:   i + 1,
				Parent: parent,
			})
			currentFunc = name
			continue
		}

		// 顶层赋值
		if ws == 0 {
			if m := pyAssignRe.FindStringSubmatch(line); m != nil {
				r.varRefs = append(r.varRefs, store.VarRef{
					VarName: m[1],
					Action:  "write",
					Line:    i + 1,
				})
			}
		}

		// 调用：粗粒度抽取，跳过关键字与常见内置
		if currentFunc != "" || ws > 0 {
			for _, m := range pyCallRe.FindAllStringSubmatch(line, -1) {
				name := m[1]
				if _, isKw := pyKeywordSet[name]; isKw {
					continue
				}
				caller := currentFunc
				if caller == "" {
					caller = "<module>"
				}
				r.calls = append(r.calls, store.Call{
					Caller: caller,
					Callee: name,
					Line:   i + 1,
				})
			}
		}
	}
	_ = relPath
	return r
}

// stripPyComment 删除 # 之后的部分，但不破坏字符串里的 #。
//
// 简化处理：仅对最朴素的「双引号 / 单引号字符串」做忽略；
// 复杂场景（嵌套 / 转义）不解析，必要时让正则在残留上失败即可。
func stripPyComment(line string) string {
	var b strings.Builder
	inS, inD := false, false
	for i := 0; i < len(line); i++ {
		c := line[i]
		if c == '\\' && i+1 < len(line) {
			b.WriteByte(c)
			b.WriteByte(line[i+1])
			i++
			continue
		}
		if c == '\'' && !inD {
			inS = !inS
		} else if c == '"' && !inS {
			inD = !inD
		}
		if c == '#' && !inS && !inD {
			break
		}
		b.WriteByte(c)
	}
	return b.String()
}

// openingDocstring 检测一行是否「起」了一个 """ 或 ''' 块。
// 返回开启用到的定界符；未开启返回 ""。
func openingDocstring(line string) string {
	for _, d := range []string{`"""`, `'''`} {
		if i := strings.Index(line, d); i >= 0 {
			rest := line[i+len(d):]
			if !strings.Contains(rest, d) {
				return d
			}
		}
	}
	return ""
}

// indentOf 返回行首的空白数。
func indentOf(line string) int {
	n := 0
	for _, c := range line {
		if c == ' ' || c == '\t' {
			n++
		} else {
			break
		}
	}
	return n
}

// splitImportItems 把 from a import b, c as d, e 中的 b/c/e 还原成切片。
func splitImportItems(s string) []string {
	s = strings.TrimSpace(s)
	s = strings.TrimPrefix(s, "(")
	s = strings.TrimSuffix(s, ")")
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if i := strings.Index(p, " as "); i >= 0 {
			p = strings.TrimSpace(p[:i])
		}
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

// splitClassParents 解析 class Foo(A, B, metaclass=M) 中的 A、B；
// 形如 metaclass= 的关键字参数会被丢弃。
func splitClassParents(inner string) []string {
	if inner == "" {
		return nil
	}
	parts := strings.Split(inner, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p == "" || strings.Contains(p, "=") {
			continue
		}
		out = append(out, p)
	}
	return out
}

// countCodeLines 统计「非空、非纯注释」的有效行数。
//
// language 暂未用，预留给后续做更精细的统计差异。
func countCodeLines(lines []string, language string) int {
	_ = language
	n := 0
	inDoc := false
	delim := ""
	for _, raw := range lines {
		l := strings.TrimSpace(raw)
		if l == "" {
			continue
		}
		if inDoc {
			if strings.Contains(l, delim) {
				inDoc = false
			}
			continue
		}
		if d := openingDocstring(l); d != "" {
			// 同行起止视为一行注释 / 文档
			rest := l[strings.Index(l, d)+len(d):]
			if !strings.Contains(rest, d) {
				inDoc = true
				delim = d
			}
			continue
		}
		if strings.HasPrefix(l, "#") {
			continue
		}
		n++
	}
	return n
}
