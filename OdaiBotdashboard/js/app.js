// Utilities
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}/${pad(d.getMonth()+1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Router
const Router = {
  routes: {
    '#/login':                LoginPage,
    '#/register':             RegisterPage,
    '#/reset-password':       ResetPasswordPage,
    '#/dashboard':            DashboardPage,
    '#/dashboard/users':      UsersPage,
    '#/dashboard/tags':       TagsPage,
    '#/dashboard/odai':       OdaiPage,
    '#/dashboard/schedules':  SchedulesPage,
    '#/dashboard/settings':   SettingsPage,
  },

  _isAuth() { return !!localStorage.getItem('access_token'); },

  async navigate(rawHash) {
    const routeKey = (rawHash || '').split('?')[0] || '#/login';

    if (routeKey.startsWith('#/dashboard') && !this._isAuth()) {
      location.hash = '#/login';
      return;
    }
    const hashQuery = (rawHash || '').includes('?') ? (rawHash || '').split('?')[1] : '';
    const hashParams = new URLSearchParams(hashQuery);
    const hasInvite = hashParams.has('invite');
    const isInvitePage = (routeKey === '#/register' || routeKey === '#/reset-password') && hasInvite;
    if ((routeKey === '#/login' || !isInvitePage && (routeKey === '#/register' || routeKey === '#/reset-password')) && this._isAuth()) {
      location.hash = '#/dashboard';
      return;
    }

    const page = this.routes[routeKey];
    if (!page) {
      location.hash = this._isAuth() ? '#/dashboard' : '#/login';
      return;
    }

    const app = document.getElementById('app');
    const html = await page.render();
    app.innerHTML = html;
    await page.init();
  },

  init() {
    window.addEventListener('hashchange', () => this.navigate(location.hash));
    this.navigate(location.hash || '#/login');
  },
};

Router.init();
