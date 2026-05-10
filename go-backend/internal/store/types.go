// Package store 中的领域类型定义。
//
// 这些结构体既是 SQL 行的映射载体（带 db tag），
// 也是上层分析模块之间传递数据的中间表示，
// 集中放在 store 是为了所有解析/分析模块拿到的形状一致，
// 减少不同包之间转换样板。
package store

import "time"

// Module 表示一个源文件级的模块节点（图中的顶点）。
//
// ModuleID 选择规则：Python 用「以 . 连接的相对包路径，去掉 .py」，
// Java 用「package + class 主名」。这样跨语言都能用纯字符串 key 做 map 查找。
type Module struct {
	ScanID   int64  `db:"scan_id"`
	ModuleID string `db:"module_id"`
	FilePath string `db:"file_path"`
	Language string `db:"language"`
	LOC      int    `db:"loc"`
	FanIn    int    `db:"fan_in"`
	FanOut   int    `db:"fan_out"`
	Layer    string `db:"layer"`
}

// Edge 表示一条模块间依赖（import / call）。
//
// IsWildcard=1 表示 Python `from x import *` 之类的全量导入，
// 在循环检测时这种边权重更高（破坏力更强）。
type Edge struct {
	ScanID     int64  `db:"scan_id"`
	Src        string `db:"src"`
	Dst        string `db:"dst"`
	Kind       string `db:"kind"` // import / call / inherit
	Count      int    `db:"count"`
	IsWildcard int    `db:"is_wildcard"`
}

// Symbol 是一个被命名的代码实体（class / function / var）。
//
// Parent 用于把 method 归并到 class，Python 嵌套函数也可借此构成树。
type Symbol struct {
	ID       int64  `db:"id"`
	ScanID   int64  `db:"scan_id"`
	Name     string `db:"name"`
	Kind     string `db:"kind"` // class / function / method / var / interface / enum
	FilePath string `db:"file_path"`
	Line     int    `db:"line"`
	Parent   string `db:"parent"`
}

// Call 是一次调用关系，caller -> callee。
type Call struct {
	ID       int64  `db:"id"`
	ScanID   int64  `db:"scan_id"`
	Caller   string `db:"caller"`
	Callee   string `db:"callee"`
	FilePath string `db:"file_path"`
	Line     int    `db:"line"`
}

// VarRef 标记一次变量使用：read / write。
type VarRef struct {
	ID       int64  `db:"id"`
	ScanID   int64  `db:"scan_id"`
	VarName  string `db:"var_name"`
	Action   string `db:"action"`
	FilePath string `db:"file_path"`
	Line     int    `db:"line"`
}

// Cycle 是一组相互依赖的模块（一个 SCC 中 size>=2 的环）。
type Cycle struct {
	ID          int64  `db:"id"`
	ScanID      int64  `db:"scan_id"`
	Size        int    `db:"size"`
	Severity    string `db:"severity"` // minor / major / critical
	ModulesJSON string `db:"modules_json"`
	PathJSON    string `db:"path_json"`
}

// Pattern 是一次模式识别结果。
type Pattern struct {
	ID         int64   `db:"id"`
	ScanID     int64   `db:"scan_id"`
	Pattern    string  `db:"pattern"`
	Confidence float64 `db:"confidence"`
	Evidence   string  `db:"evidence"`
}

// Violation 是一次架构违规：分层倒置 / 过度设计 / God Class 等。
type Violation struct {
	ID       int64  `db:"id"`
	ScanID   int64  `db:"scan_id"`
	Kind     string `db:"kind"` // layer / godclass / overeng / longmethod
	Src      string `db:"src"`
	Dst      string `db:"dst"`
	Severity string `db:"severity"`
	Detail   string `db:"detail"`
}

// Hotspot 是综合得分较低的模块（雷达低维度的代表）。
type Hotspot struct {
	ID       int64   `db:"id"`
	ScanID   int64   `db:"scan_id"`
	ModuleID string  `db:"module_id"`
	Score    float64 `db:"score"`
	Reason   string  `db:"reason"`
}

// Radar 是一次扫描的六维架构雷达。
type Radar struct {
	ScanID     int64   `db:"scan_id"`
	Clarity    float64 `db:"clarity"`
	Isolation  float64 `db:"isolation"`
	Decoupling float64 `db:"decoupling"`
	Cohesion   float64 `db:"cohesion"`
	Discipline float64 `db:"discipline"`
	Redundancy float64 `db:"redundancy"`
	UpdatedAt  string  `db:"updated_at"`
}

// ERTable / ERColumn / ERRelation 用于持久化推断出的 ER 模型。
type ERTable struct {
	ScanID     int64  `db:"scan_id"`
	TableName  string `db:"table_name"`
	SourceFile string `db:"source_file"`
}

type ERColumn struct {
	ScanID    int64  `db:"scan_id"`
	TableName string `db:"table_name"`
	ColName   string `db:"col_name"`
	ColType   string `db:"col_type"`
	IsPK      int    `db:"is_pk"`
	IsFK      int    `db:"is_fk"`
	FKTable   string `db:"fk_table"`
	FKCol     string `db:"fk_col"`
}

type ERRelation struct {
	ID        int64  `db:"id"`
	ScanID    int64  `db:"scan_id"`
	FromTable string `db:"from_table"`
	ToTable   string `db:"to_table"`
	Kind      string `db:"kind"`
}

// VersionInfo 是从 Python 端表 versions 读出的本次扫描元信息，
// archd 用它来定位磁盘上待解析的源文件目录。
type VersionInfo struct {
	VersionID  int64     `db:"id"`
	ProjectID  int64     `db:"project_id"`
	UploadPath string    `db:"upload_path"`
	UploadedAt time.Time `db:"uploaded_at"`
}

// SourceFileInfo 来自 Python 端 source_files 表，标定语言归属。
type SourceFileInfo struct {
	ID           int64  `db:"id"`
	VersionID    int64  `db:"version_id"`
	RelativePath string `db:"relative_path"`
	Language     string `db:"language"`
	LinesOfCode  int    `db:"lines_of_code"`
	TotalLines   int    `db:"total_lines"`
}
