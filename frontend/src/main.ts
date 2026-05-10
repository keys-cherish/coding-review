import './style.css';
import './styles/visualization.css';
import { mountLayout } from './components/Layout';
import { routes, router } from './router';
import { toast } from './components/Toast';

const app = document.getElementById('app')!;

// 全局错误提示
window.addEventListener('unhandledrejection', (e) => {
    console.error(e);
    toast.error('未处理的错误，请查看控制台');
});

// 挂载侧边栏 + 顶栏 + 内容区
mountLayout(app);

// 启动路由（默认首页）
router.start(routes);
