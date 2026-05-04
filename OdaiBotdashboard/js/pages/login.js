const LoginPage = {
  render() {
    return `
      <div class="auth-page">
        <div class="auth-card">
          <div class="auth-card__header">
            <h2>🤖 お題Bot Dashboard</h2>
            <p>ログイン</p>
          </div>
          <form id="login-form" class="form">
            <div class="form__group">
              <label class="form__label">ユーザー名</label>
              <input type="text" id="username" class="form__input" placeholder="ユーザー名" autocomplete="username" required>
            </div>
            <div class="form__group">
              <label class="form__label">パスワード</label>
              <input type="password" id="password" class="form__input" placeholder="パスワード" autocomplete="current-password" required>
            </div>
            <div id="error-msg" class="form__error" hidden></div>
            <button type="submit" class="btn btn--primary btn--full" id="login-btn">ログイン</button>
          </form>
          <div class="auth-card__footer">
            <a href="#/register" class="link">招待登録はこちら</a>
            <span class="auth-card__footer-sep">|</span>
            <a href="#/reset-password" class="link">パスワードを忘れた場合はこちら</a>
          </div>
        </div>
      </div>
    `;
  },
  init() {
    const form = document.getElementById('login-form');
    const errorEl = document.getElementById('error-msg');
    const btn = document.getElementById('login-btn');

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;

      errorEl.hidden = true;
      btn.disabled = true;
      btn.textContent = 'ログイン中...';

      try {
        const data = await API.loginGlobal(username, password);
        const guilds = data.guilds || [];
        if (!guilds.length) throw new Error('所属するサーバーが見つかりません');

        const first = guilds[0];
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('guilds', JSON.stringify(guilds));
        localStorage.setItem('guild_id', first.guild_id);
        localStorage.setItem('guild_name', first.guild_name || first.guild_id);
        localStorage.setItem('role', first.role);
        localStorage.setItem('user', JSON.stringify({ username: data.display_name || username }));
        location.hash = '#/dashboard';
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
      } finally {
        btn.disabled = false;
        btn.textContent = 'ログイン';
      }
    });
  },
};
