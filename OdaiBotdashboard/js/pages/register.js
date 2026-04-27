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
          <form id="register-form" class="form">
            <div class="form__group">
              <label class="form__label">サーバー名</label>
              <p id="guild-name-display" class="form__note" style="font-weight:600;font-size:15px;padding:6px 0;">読み込み中...</p>
            </div>
            <input type="hidden" id="guild-id" value="${escapeHtml(guildId)}">
            <input type="hidden" id="invite-token" value="${escapeHtml(inviteToken)}">
            <div class="form__group">
              <label class="form__label">パスワード</label>
              <input type="password" id="password" class="form__input" placeholder="8文字以上" autocomplete="new-password" required>
            </div>
            <div class="form__group">
              <label class="form__label">パスワード確認</label>
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
  async init() {
    const form = document.getElementById('register-form');
    const errorEl = document.getElementById('error-msg');
    const btn = document.getElementById('register-btn');
    const guildId = document.getElementById('guild-id').value;
    const nameEl = document.getElementById('guild-name-display');

    try {
      const res = await API.getGuildName(guildId);
      nameEl.textContent = res.guild_name || guildId;
    } catch (_) {
      nameEl.textContent = guildId;
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const guildId = document.getElementById('guild-id').value.trim();
      const inviteToken = document.getElementById('invite-token').value.trim();
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
      if (!inviteToken) {
        errorEl.textContent = '招待トークンが指定されていません。招待リンクから再度アクセスしてください。';
        errorEl.hidden = false;
        return;
      }

      btn.disabled = true;
      btn.textContent = '登録中...';

      try {
        const data = await API.register(guildId, inviteToken, password);
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('role', data.role);
        localStorage.setItem('user', JSON.stringify({ username: '' }));

        // 所属 guild 一覧を取得してサーバー切替に備える
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
