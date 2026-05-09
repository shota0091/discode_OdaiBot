const Layout = {
  render(pageTitle, contentHTML) {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const guildId = localStorage.getItem('guild_id') || '';
    const guildName = localStorage.getItem('guild_name') || guildId;
    const role = localStorage.getItem('role') || 'user';
    const isAdmin = role === 'admin';
    const guilds = JSON.parse(localStorage.getItem('guilds') || '[]');
    const hash = location.hash.split('?')[0];

    const planName = localStorage.getItem('plan_name') || 'free';
    const isPro = planName === 'pro' || planName === 'enterprise';

    const navItems = [
      { href: '#/dashboard', label: 'ダッシュボード', icon: '🏠' },
      { href: '#/dashboard/plan', label: 'プラン', icon: '💳' },
      ...(isPro ? [
        { href: '#/dashboard/odai', label: 'お題管理', icon: '🖼️' },
        { href: '#/dashboard/tags', label: 'タグ管理', icon: '🏷️' },
        { href: '#/dashboard/schedules', label: 'スケジュール管理', icon: '📅' },
        { href: '#/dashboard/settings', label: '設定', icon: '⚙️' },
        ...(isAdmin ? [
          { href: '#/dashboard/users', label: 'ユーザー管理', icon: '👥' },
          { href: '#/dashboard/invites', label: '招待管理', icon: '🔗' },
        ] : []),
      ] : []),
    ];

    const guildWidget = guilds.length > 1
      ? `<select id="guild-switcher" class="guild-switcher" title="サーバーを切り替える">
           ${guilds.map(g => `<option value="${escapeHtml(g.guild_id)}" ${g.guild_id === guildId ? 'selected' : ''}>${escapeHtml(g.guild_name || g.guild_id)}</option>`).join('')}
         </select>`
      : `<div class="sidebar__guild" title="Guild ID: ${escapeHtml(guildId)}">
           <small>Guild</small><br>${escapeHtml(guildName || guildId)}
         </div>`;

    return `
      <div class="layout">
        <div class="sidebar-overlay" id="sidebar-overlay"></div>
        <aside class="sidebar" id="sidebar">
          <div class="sidebar__brand">🤖 お題Bot</div>
          ${guildWidget}
          <nav class="sidebar__nav">
            ${navItems.map(item => `
              <a href="${item.href}" class="sidebar__link ${hash === item.href ? 'sidebar__link--active' : ''}">
                <span class="sidebar__icon">${item.icon}</span>${item.label}
              </a>
            `).join('')}
          </nav>
        </aside>
        <div class="main-wrapper">
          <header class="topbar">
            <div class="topbar__left">
              <button class="hamburger" id="hamburger-btn" aria-label="メニューを開く">
                <span></span><span></span><span></span>
              </button>
              <h1 class="topbar__title">${pageTitle}</h1>
            </div>
            <div class="topbar__user">
              <a href="#/dashboard/profile" class="topbar__username">${escapeHtml(user.display_name || user.username || '')}</a>
              <span class="badge badge--${role}">${isAdmin ? '管理者' : 'ユーザー'}</span>
              <button class="btn btn--ghost btn--sm" id="logout-btn">ログアウト</button>
            </div>
          </header>
          <main class="content">
            ${contentHTML}
          </main>
        </div>
      </div>
    `;
  },
  bindLogout() {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        localStorage.clear();
        location.hash = '#/login';
      });
    }

    const hamburger = document.getElementById('hamburger-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (hamburger && sidebar && overlay) {
      const open = () => { sidebar.classList.add('sidebar--open'); overlay.classList.add('sidebar-overlay--show'); };
      const close = () => { sidebar.classList.remove('sidebar--open'); overlay.classList.remove('sidebar-overlay--show'); };
      hamburger.addEventListener('click', () => sidebar.classList.contains('sidebar--open') ? close() : open());
      overlay.addEventListener('click', close);
      sidebar.querySelectorAll('.sidebar__link').forEach(link => link.addEventListener('click', close));
    }

    // guild switcher
    const switcher = document.getElementById('guild-switcher');
    if (switcher) {
      switcher.addEventListener('change', async e => {
        const guilds = JSON.parse(localStorage.getItem('guilds') || '[]');
        const selected = guilds.find(g => g.guild_id === e.target.value);
        if (selected) {
          localStorage.setItem('guild_id', selected.guild_id);
          localStorage.setItem('guild_name', selected.guild_name || '');
          localStorage.setItem('role', selected.role);
          try {
            const planRes = await API.getPlan();
            localStorage.setItem('plan_name', planRes.data.plan_name || 'free');
          } catch (_) {
            localStorage.setItem('plan_name', 'free');
          }
          Router.navigate(location.hash);
        }
      });
    }
  },
};
