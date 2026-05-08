/**
 * components/widgets.js - 通用小组件
 * - GradeBadge
 * - SeverityBadge
 * - ProgressBar
 * - CodeViewer
 * - ToastContainer
 * - StatCard
 */
(function () {
  const { defineComponent, h, ref, watch, onMounted } = Vue;

  // ===== 等级徽章 =====
  window.GradeBadge = defineComponent({
    props: { grade: { type: String, default: 'D' } },
    setup(props) {
      return () => h('span', { class: `grade grade-${props.grade}` }, props.grade);
    },
  });

  // ===== 严重度徽章 =====
  window.SeverityBadge = defineComponent({
    props: { severity: { type: String, default: 'info' } },
    setup(props) {
      const map = { error: '严重', warning: '警告', info: '提示' };
      return () => h('span', { class: `badge badge-${props.severity}` },
        [
          h('span', { class: `dot dot-${props.severity}` }),
          map[props.severity] || props.severity
        ]);
    },
  });

  // ===== 进度条 =====
  window.ProgressBar = defineComponent({
    props: { progress: { type: Number, default: 0 } },
    setup(props) {
      return () => h('div', { class: 'progress' },
        h('div', { class: 'progress-fill', style: `width: ${(props.progress * 100).toFixed(1)}%` })
      );
    },
  });

  // ===== 滚动数字 =====
  window.AnimatedNumber = defineComponent({
    props: {
      value: { type: Number, default: 0 },
      duration: { type: Number, default: 800 },
      decimals: { type: Number, default: 1 },
    },
    setup(props) {
      const display = ref(0);
      function animate() {
        const start = display.value;
        const end = props.value;
        const startT = performance.now();
        function step(now) {
          const t = Math.min(1, (now - startT) / props.duration);
          const eased = 1 - Math.pow(1 - t, 3);
          display.value = start + (end - start) * eased;
          if (t < 1) requestAnimationFrame(step);
          else display.value = end;
        }
        requestAnimationFrame(step);
      }
      onMounted(animate);
      watch(() => props.value, animate);
      return () => h('span', display.value.toFixed(props.decimals));
    },
  });

  // ===== 统计卡片 =====
  window.StatCard = defineComponent({
    props: {
      label: String,
      value: [Number, String],
      hint: String,
      color: { type: String, default: 'primary' },
      icon: String,
    },
    setup(props, { slots }) {
      const colorMap = {
        primary: 'var(--primary)', success: 'var(--accent)',
        warning: 'var(--warning)', danger: 'var(--danger)',
      };
      return () => h('div', { class: 'card p-5' }, [
        h('div', { class: 'flex items-start justify-between' }, [
          h('div', null, [
            h('div', { class: 'text-app-muted text-xs uppercase tracking-wider mb-1' }, props.label),
            h('div', { class: 'text-3xl font-bold', style: `color: ${colorMap[props.color] || colorMap.primary}` },
              [slots.value ? slots.value() : props.value]),
            props.hint && h('div', { class: 'text-app-dim text-xs mt-1' }, props.hint),
          ]),
          props.icon && h('div', { class: 'text-2xl', style: `color: ${colorMap[props.color]};` },
            props.icon),
        ])
      ]);
    },
  });

  // ===== 代码片段查看器 =====
  window.CodeViewer = defineComponent({
    props: {
      code: { type: String, default: '' },
      language: { type: String, default: 'plaintext' },
      highlightLine: { type: Number, default: 0 },
      startLine: { type: Number, default: 1 },
    },
    setup(props) {
      return () => {
        const rawLines = (props.code || '').split('\n');
        const html = rawLines.map((line, i) => {
          const lineNum = props.startLine + i;
          const isHl = lineNum === props.highlightLine;
          let safe = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          let highlighted = safe;
          try {
            if (props.language && hljs.getLanguage(props.language)) {
              highlighted = hljs.highlight(line, { language: props.language, ignoreIllegals: true }).value;
            }
          } catch {}
          return `<div class="code-line ${isHl ? 'highlight' : ''}"><span class="lineno">${lineNum}</span><span style="white-space:pre">${highlighted}</span></div>`;
        }).join('');
        return h('div', { class: 'code-block py-2', innerHTML: html });
      };
    },
  });

  // ===== Toast 容器 =====
  window.ToastContainer = defineComponent({
    setup() {
      return () => h('div', null,
        Store.state.toasts.map((t, i) =>
          h('div', {
            key: t.id,
            class: `toast ${t.level}`,
            style: `top: ${24 + i * 64}px;`,
          }, [
            h('span', { class: `dot dot-${t.level === 'error' ? 'error' : t.level === 'success' ? 'success' : 'info'}` }),
            h('span', t.message),
          ])
        )
      );
    },
  });

})();
