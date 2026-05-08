/**
 * api.js - 后端 API 封装
 * 集中所有 fetch 请求，便于错误处理与统一改造。
 */
window.API = (() => {
  const BASE = '/api';

  async function http(method, path, body, extra = {}) {
    const headers = { 'Accept': 'application/json' };
    let payload;

    if (body instanceof FormData) {
      payload = body;
    } else if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      payload = JSON.stringify(body);
    }

    const res = await fetch(BASE + path, {
      method,
      headers,
      body: payload,
      ...extra,
    });
    if (!res.ok) {
      let msg = `${res.status} ${res.statusText}`;
      try {
        const data = await res.json();
        if (data.detail) msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } catch {}
      throw new Error(msg);
    }
    if (res.status === 204) return null;
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) return res.json();
    return res.text();
  }

  return {
    info:           ()                         => http('GET',    '/info'),
    health:         ()                         => http('GET',    '/health'),
    listProjects:   ()                         => http('GET',    '/projects'),
    createProject:  (data)                     => http('POST',   '/projects', data),
    getProject:     (id)                       => http('GET',    `/projects/${id}`),
    deleteProject:  (id)                       => http('DELETE', `/projects/${id}`),
    listVersions:   (id)                       => http('GET',    `/projects/${id}/versions`),
    upload:         (formData)                 => http('POST',   '/scans/upload', formData),
    startScan:      (versionId)                => http('POST',   `/scans/${versionId}/start`),
    getScan:        (id)                       => http('GET',    `/scans/${id}`),
    listScans:      (versionId)                => http('GET',    `/scans/version/${versionId}`),
    listIssues:     (scanId, params = {})      => {
      const q = new URLSearchParams(params).toString();
      return http('GET', `/issues/scan/${scanId}${q ? '?' + q : ''}`);
    },
    issueSummary:   (scanId)                   => http('GET',    `/issues/scan/${scanId}/summary`),
    listComplexity: (scanId, limit = 50)       => http('GET',    `/issues/scan/${scanId}/complexity?limit=${limit}`),
    listDuplications: (scanId)                 => http('GET',    `/issues/scan/${scanId}/duplications`),
    listRules:      (lang)                     => http('GET',    `/rules${lang ? '?language=' + lang : ''}`),
    toggleRule:     (code, enabled)            => http('PUT',    `/rules/${code}/toggle`, { enabled }),
    rulesStats:     ()                         => http('GET',    '/rules/stats'),
    generateReport: (scanId, format)           => http('POST',   `/reports/${scanId}/generate`, { format }),
    listReports:    (scanId)                   => http('GET',    `/reports/scan/${scanId}`),

    wsScanProgress: (scanId, onMsg) => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${proto}://${location.host}/ws/scans/${scanId}`);
      ws.onmessage = (e) => {
        try {
          onMsg(JSON.parse(e.data));
        } catch {}
      };
      return ws;
    },

    reportInlineUrl:   (id) => `${BASE}/reports/${id}/inline`,
    reportDownloadUrl: (id) => `${BASE}/reports/${id}/download`,
  };
})();
