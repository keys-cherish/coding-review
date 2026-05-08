/**
 * store.js - 全局 reactive 状态。
 *
 * 使用 Vue 3 reactive，跨组件共享状态：
 * - toasts 列表
 * - 当前主题信息
 */
window.Store = (() => {
  const { reactive } = Vue;

  const state = reactive({
    appInfo: null,
    toasts: [],
  });

  let _toastId = 0;

  function toast(message, level = 'info', timeout = 3000) {
    const id = ++_toastId;
    state.toasts.push({ id, message, level });
    setTimeout(() => {
      state.toasts = state.toasts.filter(t => t.id !== id);
    }, timeout);
  }

  return {
    state,
    toast,
    success: (m) => toast(m, 'success'),
    error:   (m) => toast(m, 'error', 5000),
    info:    (m) => toast(m, 'info'),
  };
})();
