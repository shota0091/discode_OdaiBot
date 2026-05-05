const UsersPage = {
  _users: [],

  render() {
    const isAdmin = localStorage.getItem('role') === 'admin';
    return Layout.render('ユーザー管理', `
      <div class="page-actions">
        ${isAdmin ? `
          <input type="text" id="user-search" class="form__input" placeholder="ユーザー名・表示名で検索" style="max-width:260px;">
          <button class="btn btn--primary" id="create-user-btn">＋ ユーザー作成</button>
        ` : ''}
      </div>
      <div id="users-table-root"><p class="loading">読み込み中...</p></div>
    `);
  },

  async init() {
    Layout.bindLogout();
    const isAdmin = localStorage.getItem('role') === 'admin';
    if (isAdmin) {
      document.getElementById('create-user-btn')?.addEventListener('click', () => this._openForm());
      document.getElementById('user-search')?.addEventListener('input', e => {
        this._renderTable(e.target.value.trim());
      });
    }
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
    const isAdmin = localStorage.getItem('role') === 'admin';
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
      <table class="table">
        <thead>
          <tr>
            <th>Discord ID</th><th>表示名</th><th>役割</th><th>作成日時</th><th>更新日時</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          ${users.map(u => {
            const canEdit = isAdmin || u.id === currentUserId;
            const canDelete = isAdmin && u.id !== currentUserId;
            return `
            <tr>
              <td>${escapeHtml(u.username)}</td>
              <td>${escapeHtml(u.display_name || '')}</td>
              <td><span class="badge badge--${u.role}">${u.role === 'admin' ? '管理者' : 'ユーザー'}</span></td>
              <td>${formatDate(u.created_at)}</td>
              <td>${formatDate(u.updated_at)}</td>
              <td class="table__actions">
                ${canEdit ? `<button class="btn btn--sm btn--secondary" data-edit="${u.id}">編集</button>` : ''}
                ${canDelete ? `<button class="btn btn--sm btn--danger" data-delete="${u.id}">削除</button>` : ''}
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    `;
    document.querySelectorAll('[data-edit]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.edit));
      btn.addEventListener('click', () => this._openForm(user));
    });
    document.querySelectorAll('[data-delete]').forEach(btn => {
      const user = users.find(u => u.id === parseInt(btn.dataset.delete));
      btn.addEventListener('click', () => this._confirmDelete(user));
    });
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
        <div class="form__group">
          <label class="form__label">パスワード${user ? '（変更する場合のみ入力）' : ' <span class="required">*</span>'}</label>
          <input type="password" id="f-password" class="form__input" placeholder="8文字以上">
        </div>
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
        const password = document.getElementById('f-password').value;
        const role = isAdmin ? document.getElementById('f-role').value : null;

        if (password && password.length < 8) {
          errorEl.textContent = 'パスワードは8文字以上で入力してください';
          errorEl.hidden = false;
          return;
        }

        const displayName = document.getElementById('f-display-name').value.trim() || null;
        try {
          if (user) {
            const data = {};
            if (password) data.password = password;
            if (role && role !== user.role) data.role = role;
            if (displayName !== (user.display_name || null)) data.display_name = displayName;
            await API.updateUser(user.id, data);
          } else {
            const username = document.getElementById('f-username').value.trim();
            if (!username) { errorEl.textContent = 'ユーザー名を入力してください'; errorEl.hidden = false; return; }
            if (!password) { errorEl.textContent = 'パスワードを入力してください'; errorEl.hidden = false; return; }
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
};
