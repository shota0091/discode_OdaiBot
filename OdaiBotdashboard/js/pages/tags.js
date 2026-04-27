const TagsPage = {
  _tags: [],

  render() {
    return Layout.render('タグ管理', `
      <div class="page-actions">
        <input type="text" id="tag-search" class="form__input form__input--sm" placeholder="タグ名で検索...">
        <button class="btn btn--primary" id="create-tag-btn">＋ タグ追加</button>
      </div>
      <div id="tags-table-root"><p class="loading">読み込み中...</p></div>
    `);
  },

  async init() {
    Layout.bindLogout();
    document.getElementById('create-tag-btn').addEventListener('click', () => this._openForm());
    document.getElementById('tag-search').addEventListener('input', async e => {
      await this._loadTags(e.target.value);
    });
    await this._loadTags();
  },

  async _loadTags(q = '') {
    try {
      const res = await API.getTags(q);
      this._tags = res.data;
      this._renderTable();
    } catch (err) {
      document.getElementById('tags-table-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _renderTable() {
    if (!this._tags.length) {
      document.getElementById('tags-table-root').innerHTML = '<p class="text-muted">タグが登録されていません。</p>';
      return;
    }
    document.getElementById('tags-table-root').innerHTML = `
      <table class="table">
        <thead>
          <tr><th>タグ名</th><th>説明</th><th>作成日時</th><th>操作</th></tr>
        </thead>
        <tbody>
          ${this._tags.map(t => `
            <tr>
              <td><span class="tag-chip">${escapeHtml(t.name)}</span></td>
              <td>${escapeHtml(t.description || '')}</td>
              <td>${formatDate(t.created_at)}</td>
              <td class="table__actions">
                <button class="btn btn--sm btn--secondary" data-edit="${t.id}">編集</button>
                <button class="btn btn--sm btn--danger" data-delete="${t.id}">削除</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
    document.querySelectorAll('[data-edit]').forEach(btn => {
      const tag = this._tags.find(t => t.id === parseInt(btn.dataset.edit));
      btn.addEventListener('click', () => this._openForm(tag));
    });
    document.querySelectorAll('[data-delete]').forEach(btn => {
      const tag = this._tags.find(t => t.id === parseInt(btn.dataset.delete));
      btn.addEventListener('click', () => this._confirmDelete(tag));
    });
  },

  _openForm(tag = null) {
    const title = tag ? 'タグ編集' : 'タグ追加';
    const body = `
      <div class="form">
        <div class="form__group">
          <label class="form__label">タグ名 <span class="required">*</span></label>
          <input type="text" id="f-name" class="form__input" value="${escapeHtml(tag?.name || '')}" placeholder="タグ名" required>
        </div>
        <div class="form__group">
          <label class="form__label">説明</label>
          <input type="text" id="f-desc" class="form__input" value="${escapeHtml(tag?.description || '')}" placeholder="説明（任意）">
        </div>
        <div id="f-error" class="form__error" hidden></div>
      </div>
    `;
    Modal.show(title, body, {
      onConfirm: async () => {
        const errorEl = document.getElementById('f-error');
        errorEl.hidden = true;
        const name = document.getElementById('f-name').value.trim();
        const description = document.getElementById('f-desc').value.trim();

        if (!name) { errorEl.textContent = 'タグ名を入力してください'; errorEl.hidden = false; return; }

        try {
          if (tag) {
            await API.updateTag(tag.id, { name, description: description || null });
          } else {
            await API.createTag(name, description || null);
          }
          Modal.close();
          Toast.success(tag ? '更新しました' : '追加しました');
          await this._loadTags();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      },
    });
  },

  _confirmDelete(tag) {
    Modal.confirm(
      'タグ削除',
      `「${escapeHtml(tag.name)}」を削除しますか？`,
      async () => {
        try {
          await API.deleteTag(tag.id);
          Toast.success('削除しました');
          await this._loadTags();
        } catch (err) {
          Toast.error(err.message);
        }
      }
    );
  },
};
