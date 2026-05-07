const InvitesPage = {
  _tab: 'issue',

  render() {
    return Layout.render('招待管理', `<div id="invites-root"><p class="loading">読み込み中...</p></div>`);
  },

  async init() {
    Layout.bindLogout();
    if (localStorage.getItem('role') !== 'admin') {
      location.hash = '#/dashboard/profile';
      return;
    }
    this._tab = 'issue';
    this._renderPage();
  },

  _renderPage() {
    document.getElementById('invites-root').innerHTML = `
      <div class="tab-bar">
        <button class="tab-btn ${this._tab === 'issue' ? 'tab-btn--active' : ''}" data-tab="issue">🔗 招待発行</button>
        <button class="tab-btn ${this._tab === 'list' ? 'tab-btn--active' : ''}" data-tab="list">📋 招待一覧</button>
      </div>
      <div id="tab-content"></div>
    `;
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this._tab = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('tab-btn--active', b.dataset.tab === this._tab));
        this._renderTab();
      });
    });
    this._renderTab();
  },

  _renderTab() {
    if (this._tab === 'issue') {
      this._renderIssueTab();
    } else {
      this._renderListTab();
    }
  },

  _renderIssueTab() {
    document.getElementById('tab-content').innerHTML = `
      <div class="section">
        <form id="invite-form" class="form form--inline">
          <div class="form__group">
            <label class="form__label">ユーザー名 <span class="required">*</span></label>
            <input type="text" id="i-username" class="form__input" placeholder="招待するユーザー名">
          </div>
          <div class="form__group">
            <label class="form__label">役割 <span class="required">*</span></label>
            <select id="i-role" class="form__select">
              <option value="user">ユーザー</option>
              <option value="admin">管理者</option>
            </select>
          </div>
          <div id="i-error" class="form__error" hidden></div>
          <button type="submit" class="btn btn--primary" id="i-invite-btn">招待リンク発行</button>
        </form>
        <div id="invite-result" hidden class="invite-result"></div>
      </div>
    `;

    document.getElementById('invite-form').addEventListener('submit', async e => {
      e.preventDefault();
      const errorEl = document.getElementById('i-error');
      const resultEl = document.getElementById('invite-result');
      errorEl.hidden = true;
      resultEl.hidden = true;
      const btn = document.getElementById('i-invite-btn');
      btn.disabled = true;

      const username = document.getElementById('i-username').value.trim();
      const role = document.getElementById('i-role').value;
      if (!username) {
        errorEl.textContent = 'ユーザー名を入力してください';
        errorEl.hidden = false;
        btn.disabled = false;
        return;
      }

      try {
        const data = await API.createInvite(username, role);
        const guildId = localStorage.getItem('guild_id') || '';
        const base = location.origin + location.pathname;
        const inviteUrl = `${base}#/register?guild_id=${encodeURIComponent(guildId)}&invite=${encodeURIComponent(data.invite_token)}`;
        resultEl.innerHTML = `
          <p><strong>招待リンクが発行されました</strong>（有効期限: ${formatDate(data.expires_at)}）</p>
          <div class="invite-url-box">
            <input type="text" id="invite-url-input" class="form__input" value="${escapeHtml(inviteUrl)}" readonly>
            <button class="btn btn--sm btn--secondary" id="copy-invite-btn">コピー</button>
          </div>
        `;
        resultEl.hidden = false;
        document.getElementById('copy-invite-btn').addEventListener('click', () => {
          navigator.clipboard.writeText(inviteUrl).then(() => Toast.success('クリップボードにコピーしました'));
        });
        document.getElementById('i-username').value = '';
        Toast.success('招待リンクを発行しました');
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
      } finally {
        btn.disabled = false;
      }
    });
  },

  async _renderListTab() {
    document.getElementById('tab-content').innerHTML = `<div class="section"><p class="loading">読み込み中...</p></div>`;
    try {
      const res = await API.getInvites();
      const invites = res.data || [];
      const guildId = localStorage.getItem('guild_id') || '';

      if (!invites.length) {
        document.getElementById('tab-content').innerHTML = `<div class="section"><p class="text-muted">有効な招待はありません。</p></div>`;
        return;
      }

      document.getElementById('tab-content').innerHTML = `
        <div class="section">
          <div class="table-scroll">
            <table class="table">
              <thead>
                <tr>
                  <th>ユーザー名</th>
                  <th>役割</th>
                  <th class="hide-mobile">有効期限</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                ${invites.map(inv => `
                  <tr>
                    <td>${escapeHtml(inv.username)}</td>
                    <td><span class="badge badge--${inv.role}">${inv.role === 'admin' ? '管理者' : 'ユーザー'}</span></td>
                    <td class="hide-mobile">${formatDate(inv.expires_at)}</td>
                    <td class="table__actions">
                      <button class="btn btn--sm btn--ghost" data-copy-inv data-token="${escapeHtml(inv.invite_token)}" data-guild="${escapeHtml(guildId)}">URLコピー</button>
                      <button class="btn btn--sm btn--danger" data-revoke="${inv.id}">取り消し</button>
                    </td>
                  </tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;

      document.querySelectorAll('[data-copy-inv]').forEach(btn => {
        btn.addEventListener('click', () => {
          const base = location.origin + location.pathname;
          const url = `${base}#/register?guild_id=${encodeURIComponent(btn.dataset.guild)}&invite=${encodeURIComponent(btn.dataset.token)}`;
          navigator.clipboard.writeText(url).then(() => Toast.success('コピーしました'));
        });
      });
      document.querySelectorAll('[data-revoke]').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (!confirm('この招待を取り消しますか？')) return;
          try {
            await API.revokeInvite(parseInt(btn.dataset.revoke));
            Toast.success('招待を取り消しました');
            this._renderListTab();
          } catch (err) {
            Toast.error(err.message);
          }
        });
      });
    } catch (err) {
      document.getElementById('tab-content').innerHTML = `<div class="section"><p class="text-error">${escapeHtml(err.message)}</p></div>`;
    }
  },
};
