// Package parser 中针对 Java 源文件的实现。
//
// 抽取范围：
//   - package / import：构造模块边
//   - class / interface / enum：类型符号 + 父类 / 实现接口
//   - 方法签名：粗略抽取（限定符 + 返回类型 + 名 + 形参）
//   - new ClassName(...) / Type.staticCall(...)：构造调用边
//
// 故意不实现：
//   - 注解参数解析
//   - 泛型参数（直接丢弃 < ... >）
//   - 内部类的完整路径（嵌套层次靠 brace stack 维护）
package parser

import (
	"regexp"
	"strings"

	"codeguard/archd/internal/store"
)

var (
	javaPackageRe = regexp.MustCompile(`^\s*package\s+([\w\.]+)\s*;`)
	javaImportRe  = regexp.MustCompile(`^\s*import\s+(static\s+)?([\w\.\*]+)\s*;`)
	javaTypeRe    = regexp.MustCompile(`^\s*(?:public\s+|private\s+|protected\s+|abstract\s+|final\s+|static\s+|sealed\s+|non-sealed\s+)*` +
		`(class|interface|enum|record)\s+([A-Za-z_]\w*)` +
		`(?:\s*<[^{]*>)?` +
		`(?:\s+extends\s+([A-Za-z_][\w\.,\s<>]*?))?` +
		`(?:\s+implements\s+([A-Za-z_][\w\.,\s<>]*?))?` +
		`\s*\{`)
	javaMethodRe = regexp.MustCompile(`^\s*(?:public\s+|private\s+|protected\s+|static\s+|final\s+|abstract\s+|synchronized\s+|native\s+|default\s+|@[A-Za-z_][\w\.]*\s*)*` +
		`(?:<[^>]*>\s*)?` +
		`([A-Za-z_][\w<>\[\],\s\.]*?)\s+` +
		`([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:throws\s+[\w\.,\s]+)?\s*\{`)
	javaCallRe    = regexp.MustCompile(`(?:\bnew\s+)?([A-Za-z_]\w*)\s*\(`)
	javaKeywordSet = map[string]struct{}{
		"if": {}, "for": {}, "while": {}, "switch": {}, "return": {}, "throw": {},
		"new": {}, "this": {}, "super": {}, "true": {}, "false": {}, "null": {},
		"void": {}, "int": {}, "long": {}, "short": {}, "byte": {}, "double": {},
		"float": {}, "boolean": {}, "char": {}, "String": {}, "Object": {},
		"try": {}, "catch": {}, "finally": {}, "synchronized": {},
		"public": {}, "private": {}, "protected": {}, "static": {}, "final": {},
		"abstract": {}, "class": {}, "interface": {}, "enum": {}, "record": {},
		"package": {}, "import": {}, "extends": {}, "implements": {},
	}
)

// parseJava 单遍解析 Java 源；通过 brace 栈维护当前类层次。
func parseJava(text, relPath string) *fileResult {
	r := &fileResult{}
	clean := stripJavaCommentsAndStrings(text)
	lines := strings.Split(clean, "\n")
	r.loc = countCodeLines(lines, "java")

	type frame struct {
		typeName string
		brace    int // 进入此类型时的累计 { 计数
	}
	stack := []frame{}
	braces := 0
	currentMethod := ""

	for i, line := range lines {
		stripped := strings.TrimSpace(line)
		if stripped == "" {
			braces += countBraceDelta(line)
			continue
		}

		// package / import
		if m := javaPackageRe.FindStringSubmatch(line); m != nil {
			braces += countBraceDelta(line)
			continue
		}
		if m := javaImportRe.FindStringSubmatch(line); m != nil {
			target := strings.TrimSuffix(m[2], ".*")
			isWild := strings.HasSuffix(m[2], ".*")
			r.rawImports = append(r.rawImports, rawImport{
				target:     target,
				kind:       "import",
				isWildcard: isWild,
			})
			braces += countBraceDelta(line)
			continue
		}

		// class / interface / enum：注意可能在多行声明上一个表达式，这里只识别同一行 { 收尾的常见写法
		if m := javaTypeRe.FindStringSubmatch(line); m != nil {
			kind := m[1] // class / interface / enum / record
			name := m[2]
			extendsList := m[3]
			implementsList := m[4]

			parent := ""
			if len(stack) > 0 {
				parent = stack[len(stack)-1].typeName
			}
			r.symbols = append(r.symbols, store.Symbol{
				Name:   name,
				Kind:   kind,
				Line:   i + 1,
				Parent: parent,
			})

			for _, p := range splitJavaTypeList(extendsList) {
				r.rawImports = append(r.rawImports, rawImport{
					target: p,
					kind:   "inherit",
				})
			}
			for _, p := range splitJavaTypeList(implementsList) {
				r.rawImports = append(r.rawImports, rawImport{
					target: p,
					kind:   "inherit",
				})
			}

			braces += countBraceDelta(line)
			stack = append(stack, frame{typeName: name, brace: braces})
			continue
		}

		// 方法
		if len(stack) > 0 {
			if m := javaMethodRe.FindStringSubmatch(line); m != nil {
				retType := strings.TrimSpace(m[1])
				name := m[2]
				if !isJavaTypeRefOnly(retType) && name != "" {
					parent := stack[len(stack)-1].typeName
					r.symbols = append(r.symbols, store.Symbol{
						Name:   name,
						Kind:   "method",
						Line:   i + 1,
						Parent: parent,
					})
					currentMethod = name
				}
			}
		}

		// 调用
		for _, m := range javaCallRe.FindAllStringSubmatch(line, -1) {
			name := m[1]
			if _, kw := javaKeywordSet[name]; kw {
				continue
			}
			caller := currentMethod
			if caller == "" {
				caller = "<static>"
			}
			r.calls = append(r.calls, store.Call{
				Caller: caller,
				Callee: name,
				Line:   i + 1,
			})
		}

		braces += countBraceDelta(line)

		// 退栈
		for len(stack) > 0 && braces < stack[len(stack)-1].brace {
			stack = stack[:len(stack)-1]
			currentMethod = ""
		}
	}
	_ = relPath
	return r
}

// stripJavaCommentsAndStrings 去掉 // 行注释、/* ... */ 块注释、
// 双引号字符串内容（保留引号占位），减少正则误匹配。
//
// 不处理 Java 14+ 文本块（"""...""")，但实践里 import / class 声明
// 不会嵌入文本块，对结果影响极小。
func stripJavaCommentsAndStrings(text string) string {
	var b strings.Builder
	inLine, inBlock, inStr, inChar := false, false, false, false
	for i := 0; i < len(text); i++ {
		c := text[i]
		next := byte(0)
		if i+1 < len(text) {
			next = text[i+1]
		}

		switch {
		case inLine:
			if c == '\n' {
				inLine = false
				b.WriteByte(c)
			}
		case inBlock:
			if c == '*' && next == '/' {
				inBlock = false
				i++
			} else if c == '\n' {
				b.WriteByte(c)
			}
		case inStr:
			if c == '\\' && i+1 < len(text) {
				i++
				continue
			}
			if c == '"' {
				inStr = false
				b.WriteByte(c)
			}
		case inChar:
			if c == '\\' && i+1 < len(text) {
				i++
				continue
			}
			if c == '\'' {
				inChar = false
				b.WriteByte(c)
			}
		default:
			if c == '/' && next == '/' {
				inLine = true
				i++
			} else if c == '/' && next == '*' {
				inBlock = true
				i++
			} else if c == '"' {
				inStr = true
				b.WriteByte(c)
			} else if c == '\'' {
				inChar = true
				b.WriteByte(c)
			} else {
				b.WriteByte(c)
			}
		}
	}
	return b.String()
}

// countBraceDelta 仅计算「同一行」内 { 与 } 的差，用于 brace 栈。
func countBraceDelta(line string) int {
	delta := 0
	for _, c := range line {
		if c == '{' {
			delta++
		} else if c == '}' {
			delta--
		}
	}
	return delta
}

// splitJavaTypeList 解析 `extends A, B<T>, c.d.E` 形式的类型清单。
// 移除泛型尖括号内容，按 , 切分。
func splitJavaTypeList(s string) []string {
	if s == "" {
		return nil
	}
	// 删除泛型
	for {
		l := strings.Index(s, "<")
		if l < 0 {
			break
		}
		depth := 1
		r := l + 1
		for r < len(s) && depth > 0 {
			if s[r] == '<' {
				depth++
			} else if s[r] == '>' {
				depth--
			}
			r++
		}
		if depth != 0 {
			break
		}
		s = s[:l] + s[r:]
	}
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		out = append(out, p)
	}
	return out
}

// isJavaTypeRefOnly 判断「形如 String[] map<String,Long>」这类
// 看起来是返回类型的片段；用于过滤误识别为方法的字段声明。
func isJavaTypeRefOnly(s string) bool {
	s = strings.TrimSpace(s)
	if s == "" {
		return true // 空：不是方法
	}
	// 含 `=` / `;` 的多半是字段声明的尾部
	if strings.ContainsAny(s, "=;") {
		return true
	}
	return false
}
