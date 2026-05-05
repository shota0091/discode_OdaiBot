const RegisterPage = {
  render() {
    const hashStr = location.hash;
    const queryStr = hashStr.includes('?') ? hashStr.split('?')[1] : '';
    const params = new URLSearchParams(queryStr);
    const guildId = params.get('guild_id') || '';
    const inviteToken = params.get('invite') || '';

    return `
      <div class="auth-page">
        <div class="auth-card">
          <div class="auth-card__header">
            <h2>🤖 お題Bot Dashboard</h2>
            <p>招待登録</p>
          </div>
          <div id="register-status">
            <p class="loading">確認中...</p>
          </div>
          <form id="register-form" class="form" style="display:none">
            <div class="form__group">
              <label class="form__label">サーバー名</label>
              <p id="guild-name-display" class="form__note" style="font-weight:600;font-size:15px;padding:6px 0;">読み込み中...</p>
            </div>
            <input type="hidden" id="guild-id" value="${escapeHtml(guildId)}">
            <input type="hidden" id="invite-token" value="${escapeHtml(inviteToken)}">
            <div class="form__group">
              <label class="form__label">表示名</label>
              <input type="text" id="display-name" class="form__input" placeholder="Discordの表示名（未入力なら自動設定）" autocomplete="nickname">
              <small class="form__hint">ヘッダーに表示される名前です。未入力の場合はユーザー名が使われます。</small>
            </div>
            <div class="form__group">
              <label class="form__label">パスワード <span class="required">*</span></label>
              <input type="password" id="password" class="form__input" placeholder="8文字以上" autocomplete="new-password" required>
            </div>
            <div class="form__group">
              <label class="form__label">パスワード確認 <span class="required">*</span></label>
              <input type="password" id="password-confirm" class="form__input" placeholder="パスワード確認" autocomplete="new-password" required>
            </div>
            <div id="error-msg" class="form__error" hidden></div>
            <button type="submit" class="btn btn--primary btn--full" id="register-btn">登録</button>
          </form>
          <div class="auth-card__footer">
            <a href="#/login" class="link">ログインはこちら</a>
          </div>
        </div>
      </div>
    `;
  },

  async _finalizeLogin(guildId, data) {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('role', data.role);
    localStorage.setItem('user_id', data.user_id ?? '');
    localStorage.setItem('user', JSON.stringify({ username: data.display_name || '' }));

    try {
      const guildsRes = await API.getGuilds();
      const guilds = guildsRes.data || [];
      localStorage.setItem('guilds', JSON.stringify(guilds));
      const current = guilds.find(g => g.guild_id === guildId) || guilds[0];
      if (current) {
        localStorage.setItem('guild_id', current.guild_id);
        localStorage.setItem('guild_name', current.guild_name || current.guild_id);
        localStorage.setItem('role', current.role);
      } else {
        localStorage.setItem('guild_id', guildId);
      }
    } catch (_) {
      localStorage.setItem('guild_id', guildId);
    }
  },

  async init() {
    const hashStr = location.hash;
    const queryStr = hashStr.includes('?') ? hashStr.split('?')[1] : '';
    const params = new URLSearchParams(queryStr);
    const guildId = params.get('guild_id') || '';
    const inviteToken = params.get('invite') || '';
    const statusEl = document.getElementById('register-status');

    if (!inviteToken) {
      statusEl.innerHTML = '<p class="text-error">招待トークンが指定されていません。招待リンクから再度アクセスしてください。</p>';
      return;
    }

    // パスワードなしで自動登録を試みる（他サーバーに同名ユーザーが存在する場合）
    try {
      const data = await API.register(guildId, inviteToken);
      await this._finalizeLogin(guildId, data);
      Toast.success('登録が完了しました');
      location.hash = '#/dashboard';
      return;
    } catch (err) {
      if (err.message !== 'password_required') {
        statusEl.innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
        return;
      }
    }

    // 自動登録できなかった場合はパスワード入力フォームを表示
    statusEl.style.display = 'none';
    const form = document.getElementById('register-form');
    form.style.display = '';

    try {
      const res = await API.getGuildName(guildId);
      document.getElementById('guild-name-display').textContent = res.guild_name || guildId;
    } catch (_) {
      document.getElementById('guild-name-display').textContent = guildId;
    }

    try {
      const info = await API.getInviteInfo(guildId, inviteToken);
      if (info && info.username) {
        document.getElementById('display-name').placeholder = info.username;
        document.getElementById('display-name').value = info.username;
      }
    } catch (_) {}

    const errorEl = document.getElementById('error-msg');
    const btn = document.getElementById('register-btn');

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const password = document.getElementById('password').value;
      const passwordConfirm = document.getElementById('password-confirm').value;

      errorEl.hidden = true;

      if (password !== passwordConfirm) {
        errorEl.textContent = 'パスワードが一致しません';
        errorEl.hidden = false;
        return;
      }
      if (password.length < 8) {
        errorEl.textContent = 'パスワードは8文字以上で入力してください';
        errorEl.hidden = false;
        return;
      }

      btn.disabled = true;
      btn.textContent = '登録中...';

      try {
        const displayName = document.getElementById('display-name').value.trim() || null;
        const data = await API.register(guildId, inviteToken, password, displayName);
        await this._finalizeLogin(guildId, data);
        Toast.success('登録が完了しました');
        location.hash = '#/dashboard';
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
      } finally {
        btn.disabled = false;
        btn.textContent = '登録';
      }
    });
  },
};
