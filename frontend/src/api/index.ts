const API_BASE = '/api';

// ============ Types ============

export interface Project {
    id: number;
    name: string;
    description: string | null;
    language: string;
    created_at: string;
    updated_at: string;
    version_count: number;
    latest_score: number | null;
    latest_grade: string | null;
}

export interface Version {
    id: number;
    project_id: number;
    version_tag: string;
    uploaded_at: string;
    total_files?: number;
    total_lines?: number;
}

export const versionApi = {
    list: (projectId: number) => request<Version[]>(`/projects/${projectId}/versions`),
};

export interface Rule {
    id: number;
    code: string;
    name: string;
    description: string | null;
    language: string;
    severity: string;
    category: string;
    enabled: boolean;
}

export interface ScanTask {
    id: number;
    version_id: number;
    status: 'pending' | 'running' | 'done' | 'failed';
    progress: number;
    overall_score: number | null;
    grade: string | null;
    issue_count: number;
    started_at: string | null;
    finished_at: string | null;
    created_at: string;
}

export interface Issue {
    id: number;
    scan_task_id: number;
    source_file_id: number;
    rule_code: string;
    category: string;
    severity: 'high' | 'medium' | 'low';
    line: number;
    column: number | null;
    end_line: number | null;
    message: string;
    code_snippet: string | null;
    suggestion: string | null;
    file_path?: string;
}

export interface ComplexityMetric {
    id: number;
    source_file_id: number;
    function_name: string;
    cyclomatic: number;
    cognitive: number;
    lines_of_code: number;
}

export interface Duplication {
    id: number;
    scan_task_id: number;
    source_file_a: string;
    source_file_b: string;
    line_start_a: number;
    line_end_a: number;
    line_start_b: number;
    line_end_b: number;
    line_length: number;
    hash: string;
}

export interface IssueSummary {
    by_severity: Record<string, number>;
    by_category: Record<string, number>;
    top_rules: { rule_code: string; count: number }[];
    top_files: { path: string; health: number; issues: number }[];
}

export interface RuleStats {
    total: number;
    enabled: number;
    disabled: number;
}

export interface SystemInfo {
    name: string;
    version: string;
    description: string;
    supported_languages: string[];
    scan_concurrency: number;
    score_weights: {
        spec: number;
        duplication: number;
        complexity: number;
    };
}

// ============ API Client ============

interface ApiResponse<T> {
    data: T | null;
    error: string | null;
}

async function request<T>(url: string, options?: RequestInit): Promise<ApiResponse<T>> {
    try {
        const res = await fetch(`${API_BASE}${url}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: '请求失败' }));
            return { data: null, error: err.detail || '请求失败' };
        }
        const data = await res.json();
        return { data, error: null };
    } catch (e) {
        return { data: null, error: '网络错误，请检查后端服务' };
    }
}

// ============ Projects API ============

export const projectApi = {
    list: () => request<Project[]>('/projects'),

    get: (id: number) => request<Project>(`/projects/${id}`),

    create: (data: { name: string; description?: string; language: string }) =>
        request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),

    delete: (id: number) =>
        request<{ ok: boolean }>(`/projects/${id}`, { method: 'DELETE' }),

    versions: (id: number) => request<Version[]>(`/projects/${id}/versions`),
};

// ============ Scans API ============

export const scanApi = {
    upload: async (projectId: number, versionTag: string, file: File) => {
        const formData = new FormData();
        formData.append('project_id', String(projectId));
        formData.append('version_tag', versionTag);
        formData.append('file', file);
        try {
            const res = await fetch(`${API_BASE}/scans/upload`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: '上传失败' }));
                return { data: null, error: err.detail || '上传失败' };
            }
            const data = await res.json();
            return { data, error: null };
        } catch (e) {
            return { data: null, error: '网络错误' };
        }
    },

    start: (versionId: number) =>
        request<ScanTask>(`/scans/${versionId}/start`, { method: 'POST' }),

    get: (scanId: number) => request<ScanTask>(`/scans/${scanId}`),

    listByVersion: (versionId: number) =>
        request<ScanTask[]>(`/scans/version/${versionId}`),
};

// ============ Issues API ============

export const issueApi = {
    list: (scanId: number, params?: { severity?: string; rule_code?: string; limit?: number }) => {
        const query = new URLSearchParams();
        if (params?.severity) query.set('severity', params.severity);
        if (params?.rule_code) query.set('rule_code', params.rule_code);
        if (params?.limit) query.set('limit', String(params.limit));
        const qs = query.toString();
        return request<Issue[]>(`/issues/scan/${scanId}${qs ? '?' + qs : ''}`);
    },

    summary: (scanId: number) =>
        request<IssueSummary>(`/issues/scan/${scanId}/summary`),

    complexity: (scanId: number) =>
        request<ComplexityMetric[]>(`/issues/scan/${scanId}/complexity`),

    duplications: (scanId: number) =>
        request<Duplication[]>(`/issues/scan/${scanId}/duplications`),

    get: (issueId: number) => request<Issue>(`/issues/${issueId}`),
};

// ============ Reports API ============

export const reportApi = {
    generate: (scanId: number, format: 'html' | 'pdf' | 'md') =>
        request('/reports/' + scanId + '/generate', {
            method: 'POST',
            body: JSON.stringify({ format }),
        }),

    list: (scanId: number) =>
        request('/reports/scan/' + scanId),
};

// ============ Rules API ============

export const ruleApi = {
    list: (language?: string) => {
        const url = language ? `/rules?language=${language}` : '/rules';
        return request<Rule[]>(url);
    },

    toggle: (code: string, enabled: boolean) =>
        request<Rule>(`/rules/${code}/toggle`, {
            method: 'PUT',
            body: JSON.stringify({ enabled }),
        }),

    stats: () => request<RuleStats>('/rules/stats'),
};

// ============ System API ============

export const systemApi = {
    health: () => request<{ status: string; name: string; version: string }>('/health'),
    info: () => request<SystemInfo>('/info'),
};

// ============ Visualization API ============

export interface VizScan {
    id: number;
    status: string;
    grade: string | null;
    overall_score: number | null;
    created_at: string | null;
    project_id: number;
    project_name: string;
    version_id: number;
    version_tag: string;
    total_issues: number;
    duplication_rate: number;
}

export interface DepGraphNode {
    id: string;
    name: string;
    file_path: string;
    category: number;
    category_name: string;
    size: number;
    loc: number;
    fan_in: number;
    fan_out: number;
    in_cycle: boolean;
}

export interface DepGraphLink { source: string; target: string; value: number; }

export interface DepCycle {
    modules: string[];
    shortest_cycle: string[];
    size: number;
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
}

export interface DepGraphPayload {
    nodes: DepGraphNode[];
    links: DepGraphLink[];
    categories: { name: string }[];
    cycles: DepCycle[];
    stats: Record<string, number>;
}

export interface CallGraphPayload {
    nodes: { id: string; name: string; file: string; complexity: number; category_name: string }[];
    links: { source: string; target: string }[];
}

export interface HierarchyNode {
    name: string;
    value?: number;
    colorValue?: number;
    cyclomatic?: number;
    children?: HierarchyNode[];
}

export interface RadarDimension { name: string; score: number; detail: string; }

export interface RadarPayload {
    dimensions: RadarDimension[];
    overall: number;
    grade: string;
    previous?: (RadarPayload & { scan_id?: number }) | null;
}

export interface ArchPattern {
    pattern: string;
    confidence: number;
    reason: string;
    evidence: string[];
}

export interface ArchLayer {
    name: string;
    dirs: string[];
    files_count: number;
}

export interface LayerViolation {
    src_file: string;
    src_layer: string;
    dst_file: string;
    dst_layer: string;
    reason: string;
    severity: string;
}

export interface LayerViolationPayload {
    violations: LayerViolation[];
    summary: {
        total_edges: number;
        classified_edges: number;
        violation_count: number;
        violation_ratio: number;
        by_severity: Record<string, number>;
        layers_present: string[];
    };
}

export interface ArchPayload {
    detected: ArchPattern[];
    primary: string;
    layers: ArchLayer[];
    top_dirs: string[];
    cross_layer_ratio: number;
    layer_violations?: LayerViolationPayload;
}

export interface UMLPayload {
    mermaid: string;
    plantuml: string;
    type: string;
    classes: {
        name: string;
        file: string;
        parents: string[];
        fields: { name: string; type?: string; visibility: string }[];
        methods: { name: string; params: string[]; returns?: string; visibility: string; is_static?: boolean }[];
    }[];
}

export interface RefactorSuggestion {
    id: string;
    category: string;
    title: string;
    rationale: string;
    targets: string[];
    effort: 'low' | 'medium' | 'high' | string;
    impact: 'low' | 'medium' | 'high' | string;
    priority: number;
    metrics: Record<string, unknown>;
}

export interface RefactorPayload {
    total: number;
    by_category: Record<string, number>;
    suggestions: RefactorSuggestion[];
}

export const visApi = {
    listScans: () => request<VizScan[]>(`/scans`),
    depGraph: (scanId: number) => request<DepGraphPayload>(`/scans/${scanId}/dependency-graph`),
    callGraph: (scanId: number) => request<CallGraphPayload>(`/scans/${scanId}/call-graph`),
    flame: (scanId: number) => request<HierarchyNode>(`/scans/${scanId}/flame`),
    treemap: (scanId: number) => request<HierarchyNode>(`/scans/${scanId}/treemap`),
    radar: (scanId: number) => request<RadarPayload>(`/scans/${scanId}/radar`),
    architecture: (scanId: number) => request<ArchPayload>(`/scans/${scanId}/architecture`),
    layerViolations: (scanId: number) =>
        request<LayerViolationPayload>(`/scans/${scanId}/layer-violations`),
    refactor: (scanId: number) => request<RefactorPayload>(`/scans/${scanId}/refactor`),
    uml: (scanId: number) => request<UMLPayload>(`/scans/${scanId}/uml?type=class`),
};
