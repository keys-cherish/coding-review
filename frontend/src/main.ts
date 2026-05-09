import './style.css';
import { renderHeader } from './components/Header';
import { renderHome } from './views/Home';
import { router } from './router';

const app = document.getElementById('app')!;

renderHeader(app);

const mainContent = document.createElement('main');
mainContent.id = 'main-content';
mainContent.className = 'app-content';
app.appendChild(mainContent);

router.navigate(renderHome);
