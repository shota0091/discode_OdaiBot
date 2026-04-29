const ResetPasswordPage = {
  render() {
    const hashStr = location.hash;
    const queryStr = hashStr.includes('?') ? hashStr.split('?')[1] : '';
    const params = new URLSearchParams(queryStr);
    const inviteToken = params.get('invite') || '';

    if (!inviteToken) {
      return `
        <div class="auth-page">
          <div class="auth-card">
            <div class="auth-card__header">
              <h2>🤖 お題Bot Dashboard</h2>
              <p>パスワードリセット</p>
            </div>
            <div class="auth-card__body">
              <p class="form__note" style="text-align:center;line-height:1.7">
                パスワードをリセットするには、<br>
                Discordで <strong>/odai_dashboard</strong> コマンドを実行し、<br>
                発行されたリセットリンクにアクセスしてください。
              </p>
            </div>
            <div class="auth-card__footer">
              <a href="#/login" class="link">ログインに戻る</a>
            </div>
          </div>
        </div>
      `;
    }

    return `
      <div class="auth-page">
        <div class="auth-card">
          <div class="auth-card__header">
            <h2>🤖 お題Bot Dashboard</h2>
            <p>パスワードリセット</p>
          </div>
          <form id="reset-form" class="form">
            <div class="form__group">
              <label class="form__label">新しいパスワード <span class="required">*</span></label>
              <input type="password" id="password" class="form__input" placeholder="8文字以上" autocomplete="new-password" required>
            </div>
            <div class="form__group">
              <label class="form__label">パスワード確認 <span class="required">*</span></label>
              <input type="password" id="password-confirm" class="form__input" placeholder="パスワード確認" autocomplete="new-password" required>
            </div>
            <div id="error-msg" class="form__error" hidden></div>
            <button type="submit" class="btn btn--primary btn--full" id="reset-btn">パスワードを変更する</button>
          </form>
          <div class="auth-card__footer">
            <a href="#/login" class="link">ログインに戻る</a>
          </div>
        </div>
      </div>
    `;
  },

  init() {
    const hashStr = location.hash;
    const queryStr = hashStr.includes('?') ? hashStr.split('?')[1] : '';
    const params = new URLSearchParams(queryStr);
    const guildId = params.get('guild_id') || '';
    const inviteToken = params.get('invite') || '';

    if (!inviteToken) return;

    const form = document.getElementById('reset-form');
    const errorEl = document.getElementById('error-msg');
    const btn = document.getElementById('reset-btn');

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
      btn.textContent = '変更中...';

      try {
        await API.resetPassword(guildId, inviteToken, password);
        Toast.success('パスワードを変更しました');
        location.hash = '#/login';
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
        btn.disabled = false;
        btn.textContent = 'パスワードを変更する';
      }
    });
  },
};
