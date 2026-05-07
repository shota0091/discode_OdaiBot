const OdaiPage = {
  _odai: [],
  _allTags: [],
  _selected: new Set(),
  _sortKey: 'added_at',
  _sortDir: 'desc',
  _filterStatus: '',

  render() {
    return Layout.render('お題管理', `
      <div class="page-actions">
        <input type="text" id="filter-filename" class="form__input form__input--sm" placeholder="ファイル名で検索...">
        <select id="filter-tag" class="form__select form__select--sm">
          <option value="">全タグ</option>
        </select>
        <select id="filter-status" class="form__select form__select--sm">
          <option value="">全て</option>
          <option value="unused">未使用</option>
          <option value="partial">一部使用済み</option>
          <option value="used">使用済み</option>
        </select>
        <button class="btn btn--ghost btn--sm" id="filter-fav-btn" title="お気に入りのみ表示">☆ お気に入り</button>
        <input type="text" id="filter-memo" class="form__input form__input--sm" placeholder="📝 メモ検索...">
        <button class="btn btn--primary" id="upload-odai-btn">＋ お題追加</button>
      </div>
      <div id="bulk-action-bar" class="bulk-action-bar" hidden>
        <span id="selected-count"></span>
        <button class="btn btn--sm btn--danger" id="bulk-delete-btn">一括削除</button>
        <button class="btn btn--sm btn--secondary" id="bulk-tag-btn">タグ一括編集</button>
      </div>
      <div id="odai-table-root"><p class="loading">読み込み中...</p></div>
    `);
  },

  async init() {
    Layout.bindLogout();
    this._filterStatus = '';
    this._filterFavoriteOnly = false;
    this._filterMemoQuery = '';

    try {
      const res = await API.getTags();
      this._allTags = res.data;
      const sel = document.getElementById('filter-tag');
      this._allTags.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.name;
        opt.textContent = t.name;
        sel.appendChild(opt);
      });
    } catch (_) {}

    document.getElementById('filter-filename').addEventListener('input', () => this._applyFilter());
    document.getElementById('filter-tag').addEventListener('change', () => this._applyFilter());
    document.getElementById('filter-status').addEventListener('change', e => {
      this._filterStatus = e.target.value;
      this._renderTable();
    });
    document.getElementById('filter-fav-btn').addEventListener('click', () => {
      this._filterFavoriteOnly = !this._filterFavoriteOnly;
      const btn = document.getElementById('filter-fav-btn');
      if (btn) {
        btn.textContent = this._filterFavoriteOnly ? '★ お気に入り' : '☆ お気に入り';
        btn.classList.toggle('btn--warning', this._filterFavoriteOnly);
        btn.classList.toggle('btn--ghost', !this._filterFavoriteOnly);
      }
      this._renderTable();
    });
    document.getElementById('filter-memo').addEventListener('input', e => {
      this._filterMemoQuery = e.target.value.trim().toLowerCase();
      this._renderTable();
    });
    document.getElementById('upload-odai-btn').addEventListener('click', () => this._openUploadForm());
    document.getElementById('bulk-delete-btn').addEventListener('click', () => this._bulkDelete());
    document.getElementById('bulk-tag-btn').addEventListener('click', () => this._openBulkTagForm());
    await this._loadOdai();
  },

  async _loadOdai(filename = '', tag = '') {
    try {
      const res = await API.getOdai(filename, tag);
      this._odai = res.data;
      for (const id of this._selected) {
        if (!this._odai.some(o => o.id === id)) this._selected.delete(id);
      }
      this._renderTable();
    } catch (err) {
      document.getElementById('odai-table-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _applyFilter() {
    const filename = document.getElementById('filter-filename').value.trim();
    const tag = document.getElementById('filter-tag').value;
    this._loadOdai(filename, tag);
  },

  _getUsageStatus(odai) {
    const count = odai.usage_count || 0;
    const total = odai.total_channels || 0;
    if (count === 0) return { label: '未使用', cls: 'unused' };
    if (total > 0 && count >= total) return { label: '使用済み', cls: 'used' };
    return { label: '一部使用済み', cls: 'partial' };
  },

  _renderTable() {
    let list = [...this._odai];

    if (this._filterStatus) {
      list = list.filter(o => this._getUsageStatus(o).cls === this._filterStatus);
    }
    if (this._filterFavoriteOnly) {
      list = list.filter(o => o.is_favorite);
    }
    if (this._filterMemoQuery) {
      list = list.filter(o => o.memo && o.memo.toLowerCase().includes(this._filterMemoQuery));
    }

    if (!list.length) {
      document.getElementById('odai-table-root').innerHTML = '<p class="text-muted">お題が登録されていません。</p>';
      this._updateBulkBar();
      return;
    }

    const sorted = list.sort((a, b) => {
      if (this._sortKey === 'is_favorite') {
        const diff = (b.is_favorite ? 1 : 0) - (a.is_favorite ? 1 : 0);
        if (diff !== 0) return this._sortDir === 'asc' ? -diff : diff;
        return new Date(b.added_at) - new Date(a.added_at);
      }
      const av = (a[this._sortKey] ?? '').toString().toLowerCase();
      const bv = (b[this._sortKey] ?? '').toString().toLowerCase();
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return this._sortDir === 'asc' ? cmp : -cmp;
    });

    const icon = (key) => {
      if (this._sortKey !== key) return '<span class="sort-icon">⇅</span>';
      return this._sortDir === 'asc'
        ? '<span class="sort-icon sort-icon--active">▲</span>'
        : '<span class="sort-icon sort-icon--active">▼</span>';
    };
    const favIcon = () => {
      if (this._sortKey !== 'is_favorite') return '<span class="sort-icon">⇅</span>';
      return this._sortDir === 'asc'
        ? '<span class="sort-icon sort-icon--active">▲</span>'
        : '<span class="sort-icon sort-icon--active">▼</span>';
    };

    document.getElementById('odai-table-root').innerHTML = `
      <div class="table-scroll">
        <table class="table">
          <thead>
            <tr>
              <th class="col-cb"><input type="checkbox" id="select-all" title="全選択"></th>
              <th class="col-fav"><button class="sort-btn" data-sort="is_favorite" title="お気に入り順">★ ${favIcon()}</button></th>
              <th><button class="sort-btn" data-sort="filename">ファイル名 ${icon('filename')}</button></th>
              <th>タグ</th>
              <th>使用状況</th>
              <th class="hide-mobile">登録者</th>
              <th class="hide-mobile"><button class="sort-btn" data-sort="added_at">登録日時 ${icon('added_at')}</button></th>
              <th class="hide-mobile"><button class="sort-btn" data-sort="updated_at">更新日時 ${icon('updated_at')}</button></th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${sorted.map(o => {
              const status = this._getUsageStatus(o);
              return `
              <tr>
                <td class="col-cb"><input type="checkbox" class="row-cb" data-id="${o.id}" ${this._selected.has(o.id) ? 'checked' : ''}></td>
                <td class="col-fav">
                  <button class="btn--fav ${o.is_favorite ? 'btn--fav--active' : ''}" data-fav="${o.id}" title="${o.is_favorite ? 'お気に入り解除' : 'お気に入りに追加'}">
                    ${o.is_favorite ? '★' : '☆'}
                  </button>
                </td>
                <td class="table__filename">
                  ${escapeHtml(o.filename)}${o.memo ? `<span class="memo-icon" title="${escapeHtml(o.memo)}">📝</span>` : ''}
                </td>
                <td>${(o.tags || []).map(t => `<span class="tag-chip">${escapeHtml(t)}</span>`).join(' ')}</td>
                <td><span class="badge badge--${status.cls}">${status.label}</span></td>
                <td class="hide-mobile">${escapeHtml(o.created_by_name || '—')}</td>
                <td class="hide-mobile">${formatDate(o.added_at)}</td>
                <td class="hide-mobile">${formatDate(o.updated_at)}</td>
                <td class="table__actions">
                  <button class="btn btn--sm btn--secondary" data-detail="${o.id}">詳細</button>
                </td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;

    document.querySelectorAll('.sort-btn[data-sort]').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.dataset.sort;
        if (this._sortKey === key) {
          this._sortDir = this._sortDir === 'asc' ? 'desc' : 'asc';
        } else {
          this._sortKey = key;
          this._sortDir = key === 'added_at' ? 'desc' : 'asc';
        }
        this._renderTable();
      });
    });

    document.getElementById('select-all').addEventListener('change', e => {
      if (e.target.checked) {
        sorted.forEach(o => this._selected.add(o.id));
      } else {
        sorted.forEach(o => this._selected.delete(o.id));
      }
      document.querySelectorAll('.row-cb').forEach(cb => { cb.checked = e.target.checked; });
      this._updateBulkBar();
    });

    document.querySelectorAll('.row-cb').forEach(cb => {
      cb.addEventListener('change', e => {
        const id = parseInt(e.target.dataset.id);
        if (e.target.checked) this._selected.add(id);
        else this._selected.delete(id);
        this._updateBulkBar();
      });
    });

    document.querySelectorAll('[data-fav]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.dataset.fav);
        const item = this._odai.find(o => o.id === id);
        if (!item) return;
        try {
          await API.updateOdai(id, { is_favorite: !item.is_favorite });
          item.is_favorite = !item.is_favorite;
          this._renderTable();
        } catch (err) {
          Toast.error(err.message);
        }
      });
    });

    document.querySelectorAll('[data-detail]').forEach(btn => {
      const item = this._odai.find(o => o.id === parseInt(btn.dataset.detail));
      btn.addEventListener('click', () => this._openDetailModal(item));
    });

    this._updateBulkBar();
  },

  _updateBulkBar() {
    const bar = document.getElementById('bulk-action-bar');
    const countEl = document.getElementById('selected-count');
    const count = this._selected.size;
    if (bar) bar.hidden = count === 0;
    if (countEl) countEl.textContent = `${count} 件選択中`;
    const all = document.getElementById('select-all');
    if (all) {
      all.checked = this._odai.length > 0 && count === this._odai.length;
      all.indeterminate = count > 0 && count < this._odai.length;
    }
  },

  async _openDetailModal(odai) {
    const tagOptions = this._allTags.map(t =>
      `<option value="${escapeHtml(t.name)}" ${(odai.tags || []).includes(t.name) ? 'selected' : ''}>${escapeHtml(t.name)}</option>`
    ).join('');

    const body = `
      <div class="detail-modal">
        <div>
          <div class="detail-preview-wrap">
            <div id="detail-img-loading" class="loading" style="padding:0">読み込み中...</div>
            <div id="detail-img-wrap" hidden>
              <img id="detail-img" class="preview-img" alt="${escapeHtml(odai.filename)}">
            </div>
          </div>
        </div>

        <div>
          <div class="detail-section__title">登録情報</div>
          <table class="detail-usage-table">
            <tbody>
              <tr><td>登録者</td><td>${escapeHtml(odai.created_by_name || '不明')}</td></tr>
              <tr><td>登録日時</td><td>${formatDate(odai.added_at)}</td></tr>
            </tbody>
          </table>
        </div>

        <div>
          <div class="detail-section__title">アクティビティ履歴</div>
          <div id="detail-history-wrap">
            <div id="detail-history"><span class="loading" style="padding:0">読み込み中...</span></div>
          </div>
        </div>

        <div>
          <div class="detail-section__title">ファイル名</div>
          <div class="detail-inline">
            <input type="text" id="detail-filename" class="form__input" value="${escapeHtml(odai.filename)}">
            <button class="btn btn--sm btn--secondary" id="detail-rename-btn">変更</button>
          </div>
        </div>

        <div>
          <div class="detail-section__title">タグ</div>
          <select id="detail-tags" class="form__select" multiple size="4">${tagOptions}</select>
          <button class="btn btn--sm btn--secondary" id="detail-tags-btn" style="margin-top:8px">タグ更新</button>
        </div>

        <div>
          <div class="detail-section__title">📝 メモ</div>
          <textarea id="detail-memo" class="form__input" rows="3" placeholder="例：2024年末までに削除予定、など">${escapeHtml(odai.memo || '')}</textarea>
          <button class="btn btn--sm btn--secondary" id="detail-memo-btn" style="margin-top:8px">メモを保存</button>
        </div>

        <div class="detail-section--danger">
          <button class="btn btn--sm btn--danger" id="detail-delete-btn">このお題を削除</button>
        </div>
      </div>
    `;

    Modal.show(escapeHtml(odai.filename), body, { className: 'modal--lg' });

    // 画像ロード
    (async () => {
      try {
        const url = await API.getOdaiImageUrl(odai.id);
        const img = document.getElementById('detail-img');
        if (!img) return;
        img.onload = () => {
          const loading = document.getElementById('detail-img-loading');
          const wrap = document.getElementById('detail-img-wrap');
          if (loading) loading.hidden = true;
          if (wrap) wrap.hidden = false;
          URL.revokeObjectURL(url);
        };
        img.src = url;
      } catch (_) {
        const loading = document.getElementById('detail-img-loading');
        if (loading) loading.textContent = '画像の読み込みに失敗しました';
      }
    })();

    // アクティビティ履歴（ページネーション付き）
    const _HISTORY_ACTIONS = {
      posted:     { icon: '📤', label: (d) => `${d || 'チャンネル'} に投稿` },
      favorited:  { icon: '⭐', label: ()  => 'お気に入りに追加' },
      unfavorited:{ icon: '☆',  label: ()  => 'お気に入りを解除' },
      tagged:     { icon: '🏷️', label: (d) => `タグ「${d}」を設定` },
      untagged:   { icon: '✂️', label: (d) => `タグ「${d}」を解除` },
    };

    let _histPage = 1;
    const PER_PAGE = 5;

    const _renderHistory = (data, page, totalPages) => {
      const items = data.length === 0
        ? '<p class="form__note" style="margin:0">履歴なし</p>'
        : `<div class="history-list">${data.map(h => {
            const def = _HISTORY_ACTIONS[h.action] || { icon: '•', label: (d) => d || h.action };
            const label = def.label(h.detail || '');
            const who = h.user_name || (h.user_id ? String(h.user_id) : 'Bot');
            return `
              <div class="history-item">
                <span class="history-icon">${def.icon}</span>
                <div class="history-body">
                  <div class="history-label">${escapeHtml(label)}</div>
                  <div class="history-meta">${escapeHtml(who)} · ${formatDate(h.created_at)}</div>
                </div>
              </div>`;
          }).join('')}</div>`;

      const pagination = totalPages > 1 ? `
        <div class="history-pagination">
          <button class="btn btn--sm btn--ghost" id="hist-prev" ${page <= 1 ? 'disabled' : ''}>← 前へ</button>
          <span class="history-page-info">${page} / ${totalPages} ページ</span>
          <button class="btn btn--sm btn--ghost" id="hist-next" ${page >= totalPages ? 'disabled' : ''}>次へ →</button>
        </div>` : '';

      return items + pagination;
    };

    const _loadHistory = async (page) => {
      _histPage = page;
      const el = document.getElementById('detail-history');
      if (!el) return;
      el.innerHTML = '<span class="loading" style="padding:0">読み込み中...</span>';
      try {
        const res = await API.getOdaiHistory(odai.id, page, PER_PAGE);
        if (!document.getElementById('detail-history')) return;
        el.innerHTML = _renderHistory(res.data, res.page, res.total_pages);
        const prev = document.getElementById('hist-prev');
        const next = document.getElementById('hist-next');
        if (prev) prev.onclick = () => _loadHistory(_histPage - 1);
        if (next) next.onclick = () => _loadHistory(_histPage + 1);
      } catch (_) {
        if (el) el.innerHTML = '<p class="text-error">履歴の取得に失敗しました</p>';
      }
    };

    _loadHistory(1);

    // ファイル名変更
    document.getElementById('detail-rename-btn')?.addEventListener('click', async () => {
      const newName = document.getElementById('detail-filename')?.value.trim();
      if (!newName || newName === odai.filename) return;
      try {
        await API.updateOdai(odai.id, { filename: newName });
        odai.filename = newName;
        Toast.success('ファイル名を変更しました');
        await this._loadOdai(
          document.getElementById('filter-filename')?.value.trim() || '',
          document.getElementById('filter-tag')?.value || '',
        );
      } catch (err) {
        Toast.error(err.message);
      }
    });

    // タグ更新
    document.getElementById('detail-tags-btn')?.addEventListener('click', async () => {
      const tags = Array.from(document.getElementById('detail-tags')?.selectedOptions || []).map(o => o.value);
      try {
        await API.updateOdai(odai.id, { tags });
        odai.tags = tags;
        Toast.success('タグを更新しました');
        await this._loadOdai(
          document.getElementById('filter-filename')?.value.trim() || '',
          document.getElementById('filter-tag')?.value || '',
        );
      } catch (err) {
        Toast.error(err.message);
      }
    });

    // メモ保存
    document.getElementById('detail-memo-btn')?.addEventListener('click', async () => {
      const memo = document.getElementById('detail-memo')?.value ?? '';
      try {
        await API.updateOdai(odai.id, { memo });
        odai.memo = memo.trim() || null;
        this._renderTable();
        Toast.success('メモを保存しました');
      } catch (err) {
        Toast.error(err.message);
      }
    });

    // 削除
    document.getElementById('detail-delete-btn')?.addEventListener('click', () => {
      Modal.close();
      this._confirmDelete(odai);
    });
  },

  async _bulkDelete() {
    const ids = [...this._selected];
    if (!ids.length) return;
    Modal.confirm(
      '一括削除',
      `選択した <strong>${ids.length}</strong> 件のお題を削除しますか？この操作は取り消せません。`,
      async () => {
        let failed = 0;
        for (const id of ids) {
          try { await API.deleteOdai(id); }
          catch (_) { failed++; }
        }
        this._selected.clear();
        if (failed) {
          Toast.error(`${ids.length - failed} 件削除、${failed} 件失敗`);
        } else {
          Toast.success(`${ids.length} 件削除しました`);
        }
        await this._loadOdai();
      }
    );
  },

  _openBulkTagForm() {
    const ids = [...this._selected];
    if (!ids.length) return;
    const tagOptions = this._allTags.map(t =>
      `<option value="${escapeHtml(t.name)}">${escapeHtml(t.name)}</option>`
    ).join('');
    const body = `
      <div class="form">
        <p class="form__note">選択した <strong>${ids.length}</strong> 件のお題にタグを設定します。<br>既存のタグは上書きされます。</p>
        <div class="form__group">
          <label class="form__label">タグ（複数選択可）</label>
          <select id="f-tags" class="form__select" multiple size="4">${tagOptions}</select>
        </div>
        <div id="f-error" class="form__error" hidden></div>
      </div>
    `;
    Modal.show('タグ一括編集', body, {
      confirmLabel: '保存',
      onConfirm: async () => {
        const errorEl = document.getElementById('f-error');
        errorEl.hidden = true;
        const tags = Array.from(document.getElementById('f-tags').selectedOptions).map(o => o.value);
        const confirmBtn = document.getElementById('modal-confirm');
        confirmBtn.disabled = true;
        confirmBtn.textContent = '更新中...';
        try {
          for (const id of ids) {
            await API.updateOdai(id, { tags });
          }
          this._selected.clear();
          Modal.close();
          Toast.success(`${ids.length} 件のタグを更新しました`);
          await this._loadOdai();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
          confirmBtn.disabled = false;
          confirmBtn.textContent = '保存';
        }
      },
    });
  },

  _openUploadForm() {
    const tagOptions = this._allTags.map(t =>
      `<option value="${escapeHtml(t.name)}">${escapeHtml(t.name)}</option>`
    ).join('');
    const body = `
      <div class="form">
        <div class="form__group">
          <label class="form__label">画像ファイル <span class="required">*</span></label>
          <input type="file" id="f-file" class="form__input" accept="image/jpeg,image/png,image/webp" multiple required>
          <small class="form__hint">jpg / png / webp、最大 8MB / ファイル。複数選択可。</small>
        </div>
        <div class="form__group">
          <label class="form__label">タグ（複数選択可）</label>
          <select id="f-tags" class="form__select" multiple size="4">${tagOptions}</select>
          <small class="form__hint">選択したタグはすべてのファイルに付与されます。</small>
        </div>
        <div id="f-file-list" class="upload-file-list" hidden></div>
        <div id="f-error" class="form__error" hidden></div>
      </div>
    `;
    Modal.show('お題追加', body, {
      confirmLabel: 'アップロード',
      onOpen: () => {
        document.getElementById('f-file').addEventListener('change', e => {
          const listEl = document.getElementById('f-file-list');
          const files = Array.from(e.target.files);
          if (!files.length) { listEl.hidden = true; return; }
          listEl.innerHTML = files.map(f =>
            `<div class="upload-file-item">
              <span class="upload-file-icon">🖼️</span>
              <span class="upload-file-name">${escapeHtml(f.name)}</span>
              <span class="upload-file-size">${(f.size / 1024).toFixed(0)} KB</span>
            </div>`
          ).join('');
          listEl.hidden = false;
        });
      },
      onConfirm: async () => {
        const errorEl = document.getElementById('f-error');
        errorEl.hidden = true;
        const fileInput = document.getElementById('f-file');
        const files = Array.from(fileInput.files);
        if (!files.length) { errorEl.textContent = 'ファイルを選択してください'; errorEl.hidden = false; return; }

        const oversized = files.filter(f => f.size > 8 * 1024 * 1024);
        if (oversized.length) {
          errorEl.textContent = `以下のファイルが 8MB を超えています: ${oversized.map(f => f.name).join(', ')}`;
          errorEl.hidden = false;
          return;
        }

        const selectedTags = Array.from(document.getElementById('f-tags').selectedOptions).map(o => o.value);
        const confirmBtn = document.getElementById('modal-confirm');
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'アップロード中...';

        try {
          if (files.length === 1) {
            const formData = new FormData();
            formData.append('file', files[0]);
            if (selectedTags.length) formData.append('tags', selectedTags.join(','));
            await API.uploadOdai(formData);
            Modal.close();
            Toast.success('アップロードしました');
          } else {
            const formData = new FormData();
            files.forEach(f => formData.append('files', f));
            if (selectedTags.length) formData.append('tags', selectedTags.join(','));
            const res = await API.importOdai(formData);
            const results = res.data;
            const succeeded = results.filter(r => r.success).length;
            const failed = results.filter(r => !r.success);
            Modal.close();
            if (failed.length === 0) {
              Toast.success(`${succeeded} 件アップロードしました`);
            } else {
              Toast.info(`${succeeded} 件成功、${failed.length} 件失敗`);
              failed.forEach(r => Toast.error(`${r.filename}: ${r.message}`));
            }
          }
          await this._loadOdai();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
          confirmBtn.disabled = false;
          confirmBtn.textContent = 'アップロード';
        }
      },
    });
  },

  _confirmDelete(odai) {
    Modal.confirm(
      'お題削除',
      `「${escapeHtml(odai.filename)}」を削除しますか？`,
      async () => {
        try {
          await API.deleteOdai(odai.id);
          Toast.success('削除しました');
          await this._loadOdai();
        } catch (err) {
          Toast.error(err.message);
        }
      }
    );
  },
};
