const UsersPage = {
  _users: [],

  render() {
    return Layout.render('ユーザー管理', `
      <div class="page-actions">
        <input type="text" id="user-search" class="form__input" placeholder="ユーザー名・表示名で検索" style="max-width:260px;">
        <button class="btn btn--ghost" id="ban-list-btn">🚫 BANリスト</button>
      </div>
      <div id="users-table-root"><p class="loading">読み込み中...</p></div>
    `);
  },

  async init() {
    Layout.bindLogout();
    if (localStorage.getItem('role') !== 'admin') {
      location.hash = '#/dashboard/profile';
      return;
    }
    document.getElementById('ban-list-btn')?.addEventListener('click', () => this._openBanList());
    document.getElementById('user-search')?.addEventListener('input', e => {
      this._renderTable(e.target.value.trim());
    });
    await this._loadUsers();
  },

  async _loadUsers() {
    try {
      const res = await API.getUsers();
      this._users = Array.isArray(res) ? res : (res.data ?? []);
      this._renderTable();
    } catch (err) {
      document.getElementById('users-table-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _renderTable(search = '') {
    const currentUserId = parseInt(localStorage.getItem('user_id') || '0');
    const q = search.toLowerCase();
    const users = q
      ? this._users.filter(u =>
          u.username.toLowerCase().includes(q) ||
          (u.display_name || '').toLowerCase().includes(q)
        )
      : this._users;

    if (!users.length) {
      document.getElementById('users-table-root').innerHTML = q
        ? `<p class="text-muted">「${escapeHtml(search)}」に一致するユーザーが見つかりません。</p>`
        : '<p class="text-muted">ユーザーが登録されていません。</p>';
      return;
    }
    document.getElementById('users-table-root').innerHTML = `
      <div class="table-scroll">
      <table class="table">
        <thead>
          <tr>
            <th>ユーザー名</th><th>表示名</th><th>役割</th><th class="hide-mobile">作成日時</th><th class="hide-mobile">更新日時</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          ${users.map(u => {
            const isSelf = u.id === currentUserId;
            const isLocked = u.login_locked || (u.locked_until && new Date(u.locked_until) > new Date());
            const isBanned = !!u.is_banned;
            const lockBadge = u.login_locked
              ? '<span class="badge badge--error" title="管理者解除が必要">永久ロック</span>'
              : isLocked
                ? `<span class="badge badge--warning" title="${u.login_attempts}回失敗">一時ロック</span>`
                : '';
            const banBadge = isBanned ? '<span class="badge badge--error">BAN</span>' : '';
            return `
            <tr${isBanned ? ' style="opacity:0.6"' : ''}>
              <td>${escapeHtml(u.username)}</td>
              <td>${escapeHtml(u.display_name || '')}</td>
              <td>
                <span class="badge badge--${u.role}">${u.role === 'admin' ? '管理者' : 'ユーザー'}</span>
                ${lockBadge}${banBadge}
              </td>
              <td class="hide-mobile">${formatDate(u.created_at)}</td>
              <td class="hide-mobile">${formatDate(u.updated_at)}</td>
              <td class="table__actions">
                <button class="btn btn--sm btn--ghost" data-detail="${u.id}">詳細</button>
                ${!isBanned ? `<button class="btn btn--sm btn--secondary" data-edit="${u.id}">編集</button>` : ''}
                ${isLocked && !isBanned ? `<button class="btn btn--sm btn--warning" data-unlock="${u.id}">解除</button>` : ''}
                ${!isBanned ? `<button class="btn btn--sm btn--ghost" data-pwreset="${u.id}">PW変更</button>` : ''}
                ${!isSelf ? (isBanned
                  ? `<button class="btn btn--sm btn--secondary" data-unban="${u.id}">BAN解除</button>`
                  : `<button class="btn btn--sm btn--danger" data-ban="${u.id}">BAN</button>`)
                  : ''}
                ${!isSelf && !isBanned ? `<button class="btn btn--sm btn--danger" data-delete="${u.id}">削除</button>` : ''}
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
      </div>
    `;
    document.querySelectorAll('[data-pwreset]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.pwreset));
      btn.addEventListener('click', () => this._openPasswordResetForm(user));
    });
    document.querySelectorAll('[data-ban]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.ban));
      btn.addEventListener('click', () => this._confirmBan(user));
    });
    document.querySelectorAll('[data-unban]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.unban));
      btn.addEventListener('click', () => this._confirmUnban(user));
    });
    document.querySelectorAll('[data-detail]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.detail));
      btn.addEventListener('click', () => this._openDetail(user));
    });
    document.querySelectorAll('[data-edit]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.edit));
      btn.addEventListener('click', () => this._openForm(user));
    });
    document.querySelectorAll('[data-unlock]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.unlock));
      btn.addEventListener('click', () => this._confirmUnlock(user));
    });
    document.querySelectorAll('[data-delete]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.delete));
      btn.addEventListener('click', () => this._confirmDelete(user));
    });
  },

  async _openDetail(user) {
    Modal.show(`${escapeHtml(user.display_name || user.username)} の詳細`, '<p class="loading">読み込み中...</p>', { confirmLabel: null });
    try {
      const res = await API.getUserProfile(user.id);
      const { created_odai, created_tags } = res;

      const odaiHTML = created_odai.length
        ? `<div class="table-scroll"><table class="table">
            <thead><tr><th>ファイル名</th><th>お気に入り</th><th class="hide-mobile">登録日時</th></tr></thead>
            <tbody>${created_odai.map(o => `
              <tr>
                <td class="table__filename">${escapeHtml(o.filename)}</td>
                <td>${o.is_favorite ? '★' : '—'}</td>
                <td class="hide-mobile">${formatDate(o.added_at)}</td>
              </tr>`).join('')}
            </tbody>
          </table></div>`
        : '<p class="text-muted" style="padding:8px 0">まだお題を登録していません。</p>';

      const tagsHTML = created_tags.length
        ? `<div class="table-scroll"><table class="table">
            <thead><tr><th>タグ名</th><th>説明</th><th>お気に入り</th></tr></thead>
            <tbody>${created_tags.map(t => `
              <tr>
                <td><span class="tag-chip">${escapeHtml(t.name)}</span></td>
                <td>${escapeHtml(t.description || '')}</td>
                <td>${t.is_favorite ? '★' : '—'}</td>
              </tr>`).join('')}
            </tbody>
          </table></div>`
        : '<p class="text-muted" style="padding:8px 0">まだタグを登録していません。</p>';

      const body = document.querySelector('.modal__body');
      if (body) {
        body.innerHTML = `
          <div style="display:flex;flex-direction:column;gap:16px">
            <div>
              <div class="detail-section__title">🖼️ 登録したお題（${created_odai.length}件）</div>
              ${odaiHTML}
            </div>
            <div>
              <div class="detail-section__title">🏷️ 登録したタグ（${created_tags.length}件）</div>
              ${tagsHTML}
            </div>
          </div>
        `;
      }
    } catch (err) {
      const body = document.querySelector('.modal__body');
      if (body) body.innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _openForm(user = null) {
    const isAdmin = localStorage.getItem('role') === 'admin';
    const title = user ? 'ユーザー編集' : 'ユーザー作成';
    const body = `
      <div class="form">
        ${!user ? `
        <div class="form__group">
          <label class="form__label">ユーザー名 <span class="required">*</span></label>
          <input type="text" id="f-username" class="form__input" placeholder="ユーザー名" required>
        </div>` : `<p class="form__note">ユーザー名: <strong>${escapeHtml(user.username)}</strong></p>`}
        <div class="form__group">
          <label class="form__label">表示名${user ? '（変更する場合のみ入力）' : ''}</label>
          <input type="text" id="f-display-name" class="form__input" placeholder="未入力の場合はユーザー名を使用" value="${escapeHtml(user?.display_name || '')}">
        </div>
        ${!user ? `
        <div class="form__group">
          <label class="form__label">パスワード <span class="required">*</span></label>
          <input type="password" id="f-password" class="form__input" placeholder="8文字以上">
        </div>` : ''}
        ${isAdmin ? `
        <div class="form__group">
          <label class="form__label">役割 <span class="required">*</span></label>
          <select id="f-role" class="form__select">
            <option value="user" ${user?.role === 'user' ? 'selected' : ''}>ユーザー</option>
            <option value="admin" ${user?.role === 'admin' ? 'selected' : ''}>管理者</option>
          </select>
        </div>` : ''}
        <div id="f-error" class="form__error" hidden></div>
      </div>
    `;
    Modal.show(title, body, {
      onConfirm: async () => {
        const errorEl = document.getElementById('f-error');
        errorEl.hidden = true;
        const role = isAdmin ? document.getElementById('f-role').value : null;
        const displayName = document.getElementById('f-display-name').value.trim() || null;
        try {
          if (user) {
            const data = {};
            if (role && role !== user.role) data.role = role;
            if (displayName !== (user.display_name || null)) data.display_name = displayName;
            await API.updateUser(user.id, data);
          } else {
            const username = document.getElementById('f-username').value.trim();
            const password = document.getElementById('f-password').value;
            if (!username) { errorEl.textContent = 'ユーザー名を入力してください'; errorEl.hidden = false; return; }
            if (!password) { errorEl.textContent = 'パスワードを入力してください'; errorEl.hidden = false; return; }
            if (password.length < 8) { errorEl.textContent = 'パスワードは8文字以上で入力してください'; errorEl.hidden = false; return; }
            await API.createUser(username, password, role || 'user', displayName);
          }
          Modal.close();
          Toast.success(user ? '更新しました' : '作成しました');
          await this._loadUsers();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      },
    });
  },

  _openPasswordResetForm(user) {
    const body = `
      <div class="form">
        <p class="form__note">ユーザー名: <strong>${escapeHtml(user.username)}</strong></p>
        <div class="form__group">
          <label class="form__label">新しいパスワード <span class="required">*</span></label>
          <input type="password" id="f-new-password" class="form__input" placeholder="8文字以上">
        </div>
        <div id="f-error" class="form__error" hidden></div>
      </div>
    `;
    Modal.show('パスワード変更', body, {
      confirmLabel: '変更',
      onConfirm: async () => {
        const errorEl = document.getElementById('f-error');
        errorEl.hidden = true;
        const password = document.getElementById('f-new-password').value;
        if (!password) { errorEl.textContent = 'パスワードを入力してください'; errorEl.hidden = false; return; }
        if (password.length < 8) { errorEl.textContent = 'パスワードは8文字以上で入力してください'; errorEl.hidden = false; return; }
        try {
          await API.updateUser(user.id, { password });
          Modal.close();
          Toast.success('パスワードを変更しました');
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      },
    });
  },

  _confirmUnlock(user) {
    Modal.confirm(
      'アカウントロック解除',
      `「${escapeHtml(user.username)}」のロックを解除しますか？`,
      async () => {
        try {
          await API.unlockUser(user.id);
          Toast.success('ロックを解除しました');
          await this._loadUsers();
        } catch (err) {
          Toast.error(err.message);
        }
      }
    );
  },

  _confirmBan(user) {
    Modal.confirm(
      'ユーザーをBAN',
      `「${escapeHtml(user.username)}」をBANしますか？<br>BANされたユーザーはこのサーバーに再参加できなくなります。`,
      async () => {
        try {
          await API.banUser(user.id);
          Toast.success('BANしました');
          await this._loadUsers();
        } catch (err) {
          Toast.error(err.message);
        }
      }
    );
  },

  _confirmUnban(user) {
    Modal.confirm(
      'BAN解除',
      `「${escapeHtml(user.username)}」のBANを解除しますか？`,
      async () => {
        try {
          await API.unbanUser(user.id);
          Toast.success('BAN解除しました');
          await this._loadUsers();
        } catch (err) {
          Toast.error(err.message);
        }
      }
    );
  },

  _confirmDelete(user) {
    Modal.confirm(
      'ユーザー削除',
      `「${escapeHtml(user.username)}」を削除しますか？この操作は取り消せません。`,
      async () => {
        try {
          await API.deleteUser(user.id);
          Toast.success('削除しました');
          await this._loadUsers();
        } catch (err) {
          Toast.error(err.message);
        }
      }
    );
  },

  async _openBanList() {
    Modal.show('BANリスト', '<p class="loading">読み込み中...</p>', {});
    try {
      const res = await API.getBans();
      const bans = res.data || [];
      const body = document.querySelector('.modal__body');
      if (!body) return;

      if (!bans.length) {
        body.innerHTML = '<p class="text-muted">BANされているユーザーはいません。</p>';
        return;
      }

      body.innerHTML = `
        <div class="table-scroll">
          <table class="table">
            <thead><tr><th>ユーザー名</th><th>BAN日時</th><th>操作</th></tr></thead>
            <tbody>
              ${bans.map(b => `
                <tr>
                  <td>${escapeHtml(b.username)}</td>
                  <td>${formatDate(b.banned_at)}</td>
                  <td><button class="btn btn--sm btn--secondary" data-remove-ban="${b.id}">解除</button></td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      `;

      body.querySelectorAll('[data-remove-ban]').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (!confirm('このBANを解除しますか？')) return;
          try {
            await API.removeBan(parseInt(btn.dataset.removeBan));
            Toast.success('BAN解除しました');
            Modal.close();
            await this._loadUsers();
          } catch (err) {
            Toast.error(err.message);
          }
        });
      });
    } catch (err) {
      const body = document.querySelector('.modal__body');
      if (body) body.innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

};
