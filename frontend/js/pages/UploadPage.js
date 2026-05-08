/**
 * UploadPage - 拖拽上传 ZIP 代码包，创建新版本。
 */
window.UploadPage = (() => {
  const { defineComponent, ref, computed, h } = Vue;

  return defineComponent({
    setup() {
      const projectId = computed(() => Number(Router.state.params.id));
      const versionTag = ref('v1.0');
      const file = ref(null);
      const dragOver = ref(false);
      const uploading = ref(false);

      function onDrop(e) {
        e.preventDefault();
        dragOver.value = false;
        if (e.dataTransfer.files.length > 0) {
          file.value = e.dataTransfer.files[0];
        }
      }
      function onSelect(e) {
        if (e.target.files.length > 0) file.value = e.target.files[0];
      }

      async function doUpload(autoStart = true) {
        if (!file.value) {
          Store.error('请选择 ZIP 文件');
          return;
        }
        if (!file.value.name.toLowerCase().endsWith('.zip')) {
          Store.error('仅支持 .zip 格式');
          return;
        }
        uploading.value = true;
        try {
          const fd = new FormData();
          fd.append('project_id', String(projectId.value));
          fd.append('version_tag', versionTag.value || 'v1.0');
          fd.append('file', file.value);
          const v = await API.upload(fd);
          Store.success(`上传成功，版本 ${v.version_tag} 已创建`);
          if (autoStart) {
            const scan = await API.startScan(v.id);
            Router.push(`/scans/${scan.id}/progress`);
          } else {
            Router.push(`/projects/${projectId.value}`);
          }
        } catch (e) {
          Store.error('上传失败: ' + e.message);
        } finally {
          uploading.value = false;
        }
      }

      return () => h('div', { class: 'max-w-3xl mx-auto px-6 py-10' }, [
        h('a', {
          class: 'text-app-muted hover:text-primary text-sm cursor-pointer',
          onClick: () => Router.push(`/projects/${projectId.value}`),
        }, '← 返回项目'),

        h('h1', { class: 'text-2xl font-bold my-4' }, '上传代码包'),
        h('p', { class: 'text-app-muted mb-6' },
          '将整个项目打包为 ZIP 文件后上传。系统会自动解压、识别源码、并启动扫描。'),

        h('div', { class: 'card p-6 mb-6' }, [
          h('label', { class: 'text-app-muted text-sm mb-2 block' }, '版本标签'),
          h('input', {
            class: 'input mb-4',
            value: versionTag.value,
            onInput: (e) => versionTag.value = e.target.value,
            placeholder: 'v1.0',
          }),

          h('div', {
            class: ['dropzone', dragOver.value ? 'drag-over' : ''],
            onDragenter: (e) => { e.preventDefault(); dragOver.value = true; },
            onDragover:  (e) => { e.preventDefault(); dragOver.value = true; },
            onDragleave: () => dragOver.value = false,
            onDrop: onDrop,
            onClick: () => document.getElementById('fileInput').click(),
          }, [
            h('div', { class: 'text-5xl mb-3' }, '📦'),
            file.value
              ? h('div', null, [
                  h('div', { class: 'text-lg text-primary font-semibold' }, file.value.name),
                  h('div', { class: 'text-app-muted text-sm mt-1' },
                    `${(file.value.size / 1024 / 1024).toFixed(2)} MB`),
                  h('div', { class: 'text-app-dim text-xs mt-2' }, '点击重选 / 拖拽替换'),
                ])
              : h('div', null, [
                  h('div', { class: 'text-lg' }, '拖拽 ZIP 到此处'),
                  h('div', { class: 'text-app-muted text-sm mt-1' }, '或点击选择文件'),
                  h('div', { class: 'text-app-dim text-xs mt-2' }, '建议大小 < 100MB'),
                ]),
            h('input', {
              id: 'fileInput', type: 'file', accept: '.zip',
              style: 'display: none', onChange: onSelect,
            }),
          ]),

          h('div', { class: 'flex gap-3 mt-6' }, [
            h('button', {
              class: 'btn btn-primary flex-1',
              onClick: () => doUpload(true),
              disabled: uploading.value,
            }, uploading.value ? '上传中...' : '🚀 上传并立即扫描'),
            h('button', {
              class: 'btn btn-ghost',
              onClick: () => doUpload(false),
              disabled: uploading.value,
            }, '仅上传'),
          ]),
        ]),

        h('div', { class: 'card p-5 text-sm text-app-muted' }, [
          h('div', { class: 'font-semibold text-app mb-2' }, '💡 提示'),
          h('ul', { class: 'list-disc list-inside space-y-1' }, [
            h('li', '系统会自动跳过 __pycache__、node_modules、.git 等无关目录'),
            h('li', '单文件超过 1MB 会自动跳过（避免分析压缩文件）'),
            h('li', '支持 Python (.py) 和 Java (.java)；同一项目可混合存在'),
            h('li', '上传的代码不会被外发，全部仅本地处理'),
          ]),
        ]),
      ]);
    },
  });
})();
