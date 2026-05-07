const ProfilePage = {
  _userId: null,
  _profile: null,

  render() {
    this._userId = parseInt(localStorage.getItem('user_id') || '0');
    return Layout.render('プロフィール', `<div id="profile-root"><p class="loading">読み込み中...</p></div>`);
  },

  async init() {
    Layout.bindLogout();
    await this._load();
  },

  async _load() {
    try {
      const res = await API.getUserProfile(this._userId);
      this._profile = res;
      this._renderProfile();
    } catch (err) {
      document.getElementById('profile-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _renderProfile() {
    const { user, created_odai, created_tags } = this._profile;

    const odaiHTML = created_odai.length
      ? `<div class="table-scroll"><table class="table">
          <thead><tr><th>ファイル名</th><th>お気に入り</th><th class="hide-mobile">登録日時</th></tr></thead>
          <tbody>
            ${created_odai.map(o => `
              <tr>
                <td class="table__filename">${escapeHtml(o.filename)}</td>
                <td>${o.is_favorite ? '<span class="btn--fav btn--fav--active">★</span>' : '<span class="btn--fav">☆</span>'}</td>
                <td class="hide-mobile">${formatDate(o.added_at)}</td>
              </tr>`).join('')}
          </tbody>
        </table></div>`
      : '<p class="text-muted">まだお題を登録していません。</p>';

    const tagsHTML = created_tags.length
      ? `<div class="table-scroll"><table class="table">
          <thead><tr><th>タグ名</th><th>説明</th><th>お気に入り</th><th class="hide-mobile">作成日時</th></tr></thead>
          <tbody>
            ${created_tags.map(t => `
              <tr>
                <td><span class="tag-chip">${escapeHtml(t.name)}</span></td>
                <td>${escapeHtml(t.description || '')}</td>
                <td>${t.is_favorite ? '<span class="btn--fav btn--fav--active">★</span>' : '<span class="btn--fav">☆</span>'}</td>
                <td class="hide-mobile">${formatDate(t.created_at)}</td>
              </tr>`).join('')}
          </tbody>
        </table></div>`
      : '<p class="text-muted">まだタグを登録していません。</p>';

    document.getElementById('profile-root').innerHTML = `
      <div class="profile-header">
        <div class="profile-header__info">
          <div class="profile-header__name">${escapeHtml(user.display_name || user.username)}</div>
          <div class="profile-header__username">@${escapeHtml(user.username)}</div>
          <div style="margin-top:6px">
            <span class="badge badge--${user.role}">${user.role === 'admin' ? '管理者' : 'ユーザー'}</span>
          </div>
        </div>
        <button class="btn btn--secondary" id="edit-profile-btn">プロフィール編集</button>
      </div>
      <div class="section">
        <h2 class="section__title">🖼️ 登録したお題（${created_odai.length}件）</h2>
        ${odaiHTML}
      </div>
      <div class="section">
        <h2 class="section__title">🏷️ 登録したタグ（${created_tags.length}件）</h2>
        ${tagsHTML}
      </div>
    `;

    document.getElementById('edit-profile-btn').addEventListener('click', () => this._openEditForm());
  },

  _openEditForm() {
    const u = this._profile.user;
    const body = `
      <div class="form">
        <p class="form__note">ユーザー名: <strong>${escapeHtml(u.username)}</strong></p>
        <div class="form__group">
          <label class="form__label">表示名（変更する場合のみ入力）</label>
          <input type="text" id="f-display-name" class="form__input" value="${escapeHtml(u.display_name || '')}" placeholder="未入力の場合はユーザー名を使用">
        </div>
        <div class="form__group">
          <label class="form__label">新しいパスワード（変更する場合のみ入力）</label>
          <input type="password" id="f-password" class="form__input" placeholder="8文字以上">
        </div>
        <div class="form__group" id="f-current-pw-group" hidden>
          <label class="form__label">現在のパスワード <span class="required">*</span></label>
          <input type="password" id="f-current-password" class="form__input" placeholder="現在のパスワードを入力">
        </div>
        <div id="f-error" class="form__error" hidden></div>
      </div>
    `;
    Modal.show('プロフィール編集', body, {
      onOpen: () => {
        document.getElementById('f-password').addEventListener('input', e => {
          document.getElementById('f-current-pw-group').hidden = !e.target.value;
        });
      },
      onConfirm: async () => {
        const errorEl = document.getElementById('f-error');
        errorEl.hidden = true;
        const password = document.getElementById('f-password').value;
        const currentPassword = document.getElementById('f-current-password').value;
        const displayName = document.getElementById('f-display-name').value.trim() || null;

        if (password && password.length < 8) {
          errorEl.textContent = 'パスワードは8文字以上で入力してください';
          errorEl.hidden = false;
          return;
        }
        if (password && !currentPassword) {
          errorEl.textContent = '現在のパスワードを入力してください';
          errorEl.hidden = false;
          return;
        }

        const data = {};
        if (password) { data.password = password; data.current_password = currentPassword; }
        if (displayName !== (u.display_name || null)) data.display_name = displayName;

        if (!Object.keys(data).length) { Modal.close(); return; }

        try {
          await API.updateUser(this._userId, data);
          if ('display_name' in data) {
            const stored = JSON.parse(localStorage.getItem('user') || '{}');
            stored.display_name = data.display_name;
            localStorage.setItem('user', JSON.stringify(stored));
          }
          Modal.close();
          Toast.success('更新しました');
          await this._load();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      },
    });
  },
};
