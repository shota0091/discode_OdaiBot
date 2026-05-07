const SettingsPage = {
  render() {
    return Layout.render('設定', `<div id="settings-root"><p class="loading">読み込み中...</p></div>`);
  },

  async init() {
    Layout.bindLogout();
    const isAdmin = localStorage.getItem('role') === 'admin';
    try {
      const res = await API.getSettings();
      const s = res.data;
      const guildId = localStorage.getItem('guild_id') || '';

      document.getElementById('settings-root').innerHTML = `
        <div class="section">
          <h2 class="section__title">サーバー情報</h2>
          <table class="table table--info">
            <tbody>
              <tr><th>サーバー名</th><td>${escapeHtml(s.guild_name || guildId)}</td></tr>
              <tr><th>Bot 状態</th><td><span class="badge badge--${s.bot_enabled ? 'success' : 'disabled'}">${s.bot_enabled ? 'ON' : 'OFF'}</span></td></tr>
              <tr><th>最終更新</th><td>${formatDate(s.updated_at)}</td></tr>
            </tbody>
          </table>
        </div>

        ${isAdmin ? `
        <div class="section">
          <h2 class="section__title">設定変更</h2>
          <form id="settings-form" class="form form--inline">
            <div class="form__group">
              <label class="form__label">Bot 有効</label>
              <select id="s-bot-enabled" class="form__select">
                <option value="true" ${s.bot_enabled ? 'selected' : ''}>ON</option>
                <option value="false" ${!s.bot_enabled ? 'selected' : ''}>OFF</option>
              </select>
            </div>
            <div class="form__group">
              <label class="form__label">タイムゾーン</label>
              <input type="text" id="s-timezone" class="form__input" value="${escapeHtml(s.timezone || 'Asia/Tokyo')}" placeholder="例: Asia/Tokyo">
            </div>
            <div id="s-error" class="form__error" hidden></div>
            <button type="submit" class="btn btn--primary" id="s-save-btn">保存</button>
          </form>
        </div>

        ` : '<p class="text-muted">設定変更は管理者のみ可能です。</p>'}
      `;

      if (isAdmin) this._bindForms();
    } catch (err) {
      document.getElementById('settings-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _bindForms() {
    document.getElementById('settings-form').addEventListener('submit', async e => {
      e.preventDefault();
      const errorEl = document.getElementById('s-error');
      errorEl.hidden = true;
      const btn = document.getElementById('s-save-btn');
      btn.disabled = true;
      try {
        const bot_enabled = document.getElementById('s-bot-enabled').value === 'true';
        const timezone = document.getElementById('s-timezone').value.trim();
        await API.updateSettings({ bot_enabled, timezone: timezone || undefined });
        Toast.success('設定を保存しました');
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
      } finally {
        btn.disabled = false;
      }
    });

  },
};
