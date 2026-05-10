// Package graph 提供 archd 内部图算法的通用实现：
// 有向图存储、入/出度统计、Tarjan 强连通分量、拓扑排序。
//
// 与外部 graph 库（gonum/graph 等）相比，这里追求两点：
//  1. 顶点 ID 是字符串（与 moduleID 完全等价，零适配成本）；
//  2. 算法的输出是「业务可直接消费」的形状（SCC 是 [][]string，
//     不是 graph.Node 的切片），避免上层再做一次抄录。
//
// 设计上把图当作不可变结构：所有变更通过 NewGraph + AddEdge 完成，
// 算法函数只读不写，方便并发查询。
package graph

import "sort"

// Graph 是字符串 ID 的简单有向图。零值不可用，必须 New。
type Graph struct {
	nodes map[string]struct{}
	out   map[string]map[string]int // src -> dst -> weight (count)
	in    map[string]map[string]int // dst -> src -> weight
}

// New 返回一个空图。
func New() *Graph {
	return &Graph{
		nodes: make(map[string]struct{}),
		out:   make(map[string]map[string]int),
		in:    make(map[string]map[string]int),
	}
}

// AddNode 添加孤立顶点（即使没有边也要保证存在，便于雷达基数统计）。
func (g *Graph) AddNode(id string) {
	g.nodes[id] = struct{}{}
}

// AddEdge 增加 src -> dst 的有向边；多次添加按 weight 累加（重边）。
//
// 自环（src == dst）一律忽略：在依赖分析里自环没有语义价值，
// 反而会让 SCC 把所有出现自我引用的节点全部当成大小为 1 的环。
func (g *Graph) AddEdge(src, dst string, weight int) {
	if src == dst {
		return
	}
	g.AddNode(src)
	g.AddNode(dst)
	if g.out[src] == nil {
		g.out[src] = make(map[string]int)
	}
	if g.in[dst] == nil {
		g.in[dst] = make(map[string]int)
	}
	g.out[src][dst] += weight
	g.in[dst][src] += weight
}

// Nodes 返回去重排序后的全部顶点 ID。
func (g *Graph) Nodes() []string {
	out := make([]string, 0, len(g.nodes))
	for n := range g.nodes {
		out = append(out, n)
	}
	sort.Strings(out)
	return out
}

// HasNode 快速判断顶点是否存在。
func (g *Graph) HasNode(id string) bool {
	_, ok := g.nodes[id]
	return ok
}

// OutNeighbors 返回 id 的出邻居（已排序，便于稳定遍历）。
func (g *Graph) OutNeighbors(id string) []string {
	m := g.out[id]
	if m == nil {
		return nil
	}
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// InNeighbors 返回 id 的入邻居（已排序）。
func (g *Graph) InNeighbors(id string) []string {
	m := g.in[id]
	if m == nil {
		return nil
	}
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// FanIn / FanOut 是按邻居数量统计（不计重边权重）。
func (g *Graph) FanIn(id string) int  { return len(g.in[id]) }
func (g *Graph) FanOut(id string) int { return len(g.out[id]) }

// EdgeWeight 返回 src->dst 的累加权重；不存在为 0。
func (g *Graph) EdgeWeight(src, dst string) int {
	if g.out[src] == nil {
		return 0
	}
	return g.out[src][dst]
}

// SCC 返回所有强连通分量；按发现顺序的逆序排列，
// 每个分量内顶点按字典序排序，便于上层稳定输出。
//
// 实现：经典 Tarjan，迭代式（避免递归在大型项目上爆栈）。
func (g *Graph) SCC() [][]string {
	type frame struct {
		node string
		iter int // 当前在邻居切片里的位置
	}
	index := 0
	indices := map[string]int{}
	lowlink := map[string]int{}
	onStack := map[string]bool{}
	var stack []string
	var result [][]string

	// Tarjan 的迭代化：用 frames 模拟递归调用栈
	all := g.Nodes()
	neighbors := map[string][]string{}
	for _, n := range all {
		neighbors[n] = g.OutNeighbors(n)
	}

	for _, start := range all {
		if _, ok := indices[start]; ok {
			continue
		}
		frames := []frame{{node: start, iter: 0}}
		indices[start] = index
		lowlink[start] = index
		index++
		stack = append(stack, start)
		onStack[start] = true

		for len(frames) > 0 {
			top := &frames[len(frames)-1]
			node := top.node
			nbrs := neighbors[node]

			if top.iter < len(nbrs) {
				w := nbrs[top.iter]
				top.iter++
				if _, visited := indices[w]; !visited {
					indices[w] = index
					lowlink[w] = index
					index++
					stack = append(stack, w)
					onStack[w] = true
					frames = append(frames, frame{node: w, iter: 0})
				} else if onStack[w] {
					if indices[w] < lowlink[node] {
						lowlink[node] = indices[w]
					}
				}
				continue
			}

			// 访问完所有邻居：向父帧回溯 lowlink
			if lowlink[node] == indices[node] {
				var comp []string
				for {
					last := stack[len(stack)-1]
					stack = stack[:len(stack)-1]
					onStack[last] = false
					comp = append(comp, last)
					if last == node {
						break
					}
				}
				sort.Strings(comp)
				result = append(result, comp)
			}
			frames = frames[:len(frames)-1]
			if len(frames) > 0 {
				parent := frames[len(frames)-1].node
				if lowlink[node] < lowlink[parent] {
					lowlink[parent] = lowlink[node]
				}
			}
		}
	}

	return result
}

// TopologicalOrder 给出无环 DAG 的 Kahn 排序结果。
// 若图含环，返回空切片 + ok=false（调用方应先 SCC 折叠）。
func (g *Graph) TopologicalOrder() (order []string, ok bool) {
	indeg := map[string]int{}
	for _, n := range g.Nodes() {
		indeg[n] = g.FanIn(n)
	}
	var queue []string
	for n, d := range indeg {
		if d == 0 {
			queue = append(queue, n)
		}
	}
	sort.Strings(queue)

	visited := 0
	for len(queue) > 0 {
		n := queue[0]
		queue = queue[1:]
		order = append(order, n)
		visited++
		nbrs := g.OutNeighbors(n)
		for _, m := range nbrs {
			indeg[m]--
			if indeg[m] == 0 {
				queue = append(queue, m)
			}
		}
		sort.Strings(queue)
	}
	if visited != len(g.nodes) {
		return nil, false
	}
	return order, true
}

// ShortestCycleThrough 返回经过节点 v 的最短简单环（包括 v 自身的回路）。
// 用于 cycle 报告里给一个直观的「path_json」示例。
//
// 算法：以 v 为起点 BFS，找到第一个能回到 v 的路径。
// 若没有这样的环，返回 nil。
func (g *Graph) ShortestCycleThrough(v string) []string {
	if !g.HasNode(v) {
		return nil
	}
	// 标准 BFS 但目标是回到 v
	type qItem struct {
		node string
		path []string
	}
	visited := map[string]bool{}
	var queue []qItem
	for _, w := range g.OutNeighbors(v) {
		queue = append(queue, qItem{node: w, path: []string{v, w}})
	}
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		if cur.node == v {
			return cur.path
		}
		if visited[cur.node] {
			continue
		}
		visited[cur.node] = true
		for _, w := range g.OutNeighbors(cur.node) {
			next := append(append([]string{}, cur.path...), w)
			queue = append(queue, qItem{node: w, path: next})
		}
	}
	return nil
}
