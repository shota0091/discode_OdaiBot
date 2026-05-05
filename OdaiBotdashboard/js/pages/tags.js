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
          <tr><th></th><th>タグ名</th><th>説明</th><th>登録者</th><th class="hide-mobile">作成日時</th><th>操作</th></tr>
        </thead>
        <tbody>
          ${this._tags.map(t => `
            <tr>
              <td class="col-fav">
                <button class="btn--fav ${t.is_favorite ? 'btn--fav--active' : ''}" data-fav="${t.id}" title="${t.is_favorite ? 'お気に入り解除' : 'お気に入りに追加'}">
                  ${t.is_favorite ? '★' : '☆'}
                </button>
              </td>
              <td><span class="tag-chip">${escapeHtml(t.name)}</span></td>
              <td>${escapeHtml(t.description || '')}</td>
              <td>${escapeHtml(t.created_by_name || '—')}</td>
              <td class="hide-mobile">${formatDate(t.created_at)}</td>
              <td class="table__actions">
                <button class="btn btn--sm btn--secondary" data-detail="${t.id}">詳細</button>
                <button class="btn btn--sm btn--ghost" data-edit="${t.id}">編集</button>
                <button class="btn btn--sm btn--danger" data-delete="${t.id}">削除</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    document.querySelectorAll('[data-fav]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.dataset.fav);
        const tag = this._tags.find(t => t.id === id);
        if (!tag) return;
        try {
          await API.updateTag(id, { is_favorite: !tag.is_favorite });
          tag.is_favorite = !tag.is_favorite;
          this._renderTable();
        } catch (err) {
          Toast.error(err.message);
        }
      });
    });

    document.querySelectorAll('[data-detail]').forEach(btn => {
      const tag = this._tags.find(t => t.id === parseInt(btn.dataset.detail));
      btn.addEventListener('click', () => this._openDetailModal(tag));
    });
    document.querySelectorAll('[data-edit]').forEach(btn => {
      const tag = this._tags.find(t => t.id === parseInt(btn.dataset.edit));
      btn.addEventListener('click', () => this._openForm(tag));
    });
    document.querySelectorAll('[data-delete]').forEach(btn => {
      const tag = this._tags.find(t => t.id === parseInt(btn.dataset.delete));
      btn.addEventListener('click', () => this._confirmDelete(tag));
    });
  },

  async _openDetailModal(tag) {
    const favLabel = tag.is_favorite ? '★ お気に入り解除' : '☆ お気に入りに追加';
    const favCls = tag.is_favorite ? 'btn--warning' : 'btn--ghost';

    const body = `
      <div class="detail-modal">
        <div>
          <div class="detail-section__title">タグ情報</div>
          <table class="detail-usage-table">
            <tbody>
              <tr><td>タグ名</td><td><span class="tag-chip">${escapeHtml(tag.name)}</span></td></tr>
              <tr><td>説明</td><td>${escapeHtml(tag.description || '—')}</td></tr>
              <tr><td>登録者</td><td>${escapeHtml(tag.created_by_name || '不明')}</td></tr>
              <tr><td>登録日時</td><td>${formatDate(tag.created_at)}</td></tr>
            </tbody>
          </table>
          <button class="btn btn--sm ${favCls}" id="detail-fav-btn" style="margin-top:10px">${favLabel}</button>
        </div>

        <div>
          <div class="detail-section__title">使用中スケジュール</div>
          <div id="detail-schedules"><span class="loading" style="padding:0">読み込み中...</span></div>
        </div>

        <div>
          <div class="detail-section__title">このタグが付いたお題</div>
          <div id="detail-odai"><span class="loading" style="padding:0">読み込み中...</span></div>
        </div>
      </div>
    `;

    Modal.show(`タグ詳細 — ${escapeHtml(tag.name)}`, body, { className: 'modal--lg' });

    document.getElementById('detail-fav-btn')?.addEventListener('click', async () => {
      try {
        await API.updateTag(tag.id, { is_favorite: !tag.is_favorite });
        tag.is_favorite = !tag.is_favorite;
        Toast.success(tag.is_favorite ? 'お気に入りに追加しました' : 'お気に入りを解除しました');
        await this._loadTags(document.getElementById('tag-search')?.value || '');
        Modal.close();
      } catch (err) {
        Toast.error(err.message);
      }
    });

    // 詳細データ取得
    try {
      const res = await API.getTagDetail(tag.id);
      const detail = res.data;

      // スケジュール
      const schedEl = document.getElementById('detail-schedules');
      if (schedEl) {
        if (!detail.schedules.length) {
          schedEl.innerHTML = '<p class="form__note" style="margin:0">このタグを使用しているスケジュールはありません</p>';
        } else {
          schedEl.innerHTML = `
            <table class="detail-usage-table">
              <thead><tr><th>チャンネル</th><th>時刻</th><th>モード</th><th>状態</th></tr></thead>
              <tbody>
                ${detail.schedules.map(s => `
                  <tr>
                    <td>${escapeHtml(s.channel_name ? '#' + s.channel_name : '—')}</td>
                    <td>${escapeHtml(s.time)}</td>
                    <td><span class="badge badge--mode">${escapeHtml(s.tag_mode)}</span></td>
                    <td>${s.enabled ? '<span class="badge badge--success">有効</span>' : '<span class="badge badge--disabled">無効</span>'}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `;
        }
      }

      // お題リスト
      const odaiEl = document.getElementById('detail-odai');
      if (odaiEl) {
        if (!detail.odai.length) {
          odaiEl.innerHTML = '<p class="form__note" style="margin:0">このタグが付いたお題はありません</p>';
        } else {
          odaiEl.innerHTML = `
            <table class="detail-usage-table">
              <thead><tr><th>ファイル名</th><th>設定者</th><th>設定日時</th></tr></thead>
              <tbody>
                ${detail.odai.map(o => `
                  <tr>
                    <td class="table__filename">${escapeHtml(o.filename)}</td>
                    <td>${escapeHtml(o.tagged_by_name || '—')}</td>
                    <td>${formatDate(o.tagged_at)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `;
        }
      }
    } catch (err) {
      const schedEl = document.getElementById('detail-schedules');
      const odaiEl = document.getElementById('detail-odai');
      if (schedEl) schedEl.innerHTML = '<p class="text-error">取得に失敗しました</p>';
      if (odaiEl) odaiEl.innerHTML = '';
    }
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
