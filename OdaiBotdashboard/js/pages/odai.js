const OdaiPage = {
  _odai: [],
  _allTags: [],
  _selected: new Set(),
  _imgCache: new Map(),
  _observer: null,

  render() {
    return Layout.render('お題管理', `
      <div class="page-actions">
        <input type="text" id="filter-filename" class="form__input form__input--sm" placeholder="ファイル名で検索...">
        <select id="filter-tag" class="form__select form__select--sm">
          <option value="">全タグ</option>
        </select>
        <select id="filter-used" class="form__select form__select--sm">
          <option value="">全て</option>
          <option value="false">未使用</option>
          <option value="true">使用済み</option>
        </select>
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
    document.getElementById('filter-used').addEventListener('change', () => this._applyFilter());
    document.getElementById('upload-odai-btn').addEventListener('click', () => this._openUploadForm());
    document.getElementById('bulk-delete-btn').addEventListener('click', () => this._bulkDelete());
    document.getElementById('bulk-tag-btn').addEventListener('click', () => this._openBulkTagForm());
    await this._loadOdai();
  },

  async _loadOdai(filename = '', tag = '', used = null) {
    try {
      const res = await API.getOdai(filename, tag, used);
      this._odai = res.data;
      for (const id of this._selected) {
        if (!this._odai.some(o => o.id === id)) this._selected.delete(id);
      }
      this._renderGrid();
    } catch (err) {
      document.getElementById('odai-table-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _applyFilter() {
    const filename = document.getElementById('filter-filename').value.trim();
    const tag = document.getElementById('filter-tag').value;
    const usedStr = document.getElementById('filter-used').value;
    const used = usedStr === '' ? null : usedStr === 'true';
    this._loadOdai(filename, tag, used);
  },

  _renderGrid() {
    if (this._observer) {
      this._observer.disconnect();
      this._observer = null;
    }

    if (!this._odai.length) {
      document.getElementById('odai-table-root').innerHTML = '<p class="text-muted">お題が登録されていません。</p>';
      this._updateBulkBar();
      return;
    }

    document.getElementById('odai-table-root').innerHTML = `
      <div class="odai-grid-header">
        <label class="odai-grid-select-all">
          <input type="checkbox" id="select-all"> 全選択
        </label>
        <span class="text-muted" style="font-size:13px">${this._odai.length} 件</span>
      </div>
      <div class="odai-grid">
        ${this._odai.map(o => `
          <div class="odai-card ${this._selected.has(o.id) ? 'is-selected' : ''}" data-id="${o.id}">
            <label class="odai-card__cb">
              <input type="checkbox" class="row-cb" data-id="${o.id}" ${this._selected.has(o.id) ? 'checked' : ''}>
            </label>
            <div class="odai-card__img-wrap">
              <div class="odai-card__placeholder">🖼️</div>
              <img class="odai-card__img lazy-img" data-odai-id="${o.id}" alt="${escapeHtml(o.filename)}">
              <div class="odai-card__overlay">
                <button class="btn btn--sm btn--secondary" data-edit="${o.id}">編集</button>
                <button class="btn btn--sm btn--danger" data-delete="${o.id}">削除</button>
              </div>
            </div>
            <div class="odai-card__meta">
              <div class="odai-card__filename" title="${escapeHtml(o.filename)}">${escapeHtml(o.filename)}</div>
              <div class="odai-card__tags">
                ${(o.tags || []).map(t => `<span class="tag-chip">${escapeHtml(t)}</span>`).join('')}
              </div>
              <span class="badge badge--${o.used ? 'used' : 'unused'}">${o.used ? '使用済み' : '未使用'}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    // 全選択チェックボックス
    const selectAll = document.getElementById('select-all');
    selectAll.checked = this._odai.length > 0 && this._selected.size === this._odai.length;
    selectAll.indeterminate = this._selected.size > 0 && this._selected.size < this._odai.length;
    selectAll.addEventListener('change', e => {
      if (e.target.checked) {
        this._odai.forEach(o => this._selected.add(o.id));
      } else {
        this._odai.forEach(o => this._selected.delete(o.id));
      }
      document.querySelectorAll('.row-cb').forEach(cb => { cb.checked = e.target.checked; });
      document.querySelectorAll('.odai-card').forEach(card => {
        card.classList.toggle('is-selected', e.target.checked);
      });
      this._updateBulkBar();
    });

    // 行チェックボックス
    document.querySelectorAll('.row-cb').forEach(cb => {
      cb.addEventListener('change', e => {
        const id = parseInt(e.target.dataset.id);
        const card = e.target.closest('.odai-card');
        if (e.target.checked) {
          this._selected.add(id);
          card.classList.add('is-selected');
        } else {
          this._selected.delete(id);
          card.classList.remove('is-selected');
        }
        this._updateBulkBar();
      });
    });

    // 編集・削除ボタン
    document.querySelectorAll('[data-edit]').forEach(btn => {
      const item = this._odai.find(o => o.id === parseInt(btn.dataset.edit));
      btn.addEventListener('click', e => { e.stopPropagation(); this._openEditForm(item); });
    });
    document.querySelectorAll('[data-delete]').forEach(btn => {
      const item = this._odai.find(o => o.id === parseInt(btn.dataset.delete));
      btn.addEventListener('click', e => { e.stopPropagation(); this._confirmDelete(item); });
    });

    // 遅延画像読み込み（Intersection Observer）
    this._observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const img = entry.target;
        const odaiId = parseInt(img.dataset.odaiId);
        this._observer.unobserve(img);
        this._loadImage(img, odaiId);
      }
    }, { rootMargin: '200px' });

    document.querySelectorAll('.lazy-img').forEach(img => this._observer.observe(img));

    this._updateBulkBar();
  },

  async _loadImage(img, odaiId) {
    try {
      let url = this._imgCache.get(odaiId);
      if (!url) {
        url = await API.getOdaiImageUrl(odaiId);
        this._imgCache.set(odaiId, url);
      }
      img.onload = () => {
        img.classList.add('loaded');
        const placeholder = img.closest('.odai-card__img-wrap').querySelector('.odai-card__placeholder');
        if (placeholder) placeholder.style.display = 'none';
      };
      img.src = url;
    } catch (_) {}
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
          this._imgCache.clear();
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

  _openEditForm(odai) {
    const tagOptions = this._allTags.map(t =>
      `<option value="${escapeHtml(t.name)}" ${(odai.tags || []).includes(t.name) ? 'selected' : ''}>${escapeHtml(t.name)}</option>`
    ).join('');
    const body = `
      <div class="form">
        <p class="form__note">ファイル名: <strong>${escapeHtml(odai.filename)}</strong></p>
        <div class="form__group">
          <label class="form__label">タグ（複数選択可）</label>
          <select id="f-tags" class="form__select" multiple size="4">${tagOptions}</select>
        </div>
        <div class="form__group">
          <label class="form__label">使用状況</label>
          <select id="f-used" class="form__select">
            <option value="false" ${!odai.used ? 'selected' : ''}>未使用</option>
            <option value="true" ${odai.used ? 'selected' : ''}>使用済み</option>
          </select>
        </div>
        <div id="f-error" class="form__error" hidden></div>
      </div>
    `;
    Modal.show('お題編集', body, {
      onConfirm: async () => {
        const errorEl = document.getElementById('f-error');
        errorEl.hidden = true;
        const tags = Array.from(document.getElementById('f-tags').selectedOptions).map(o => o.value);
        const used = document.getElementById('f-used').value === 'true';
        try {
          await API.updateOdai(odai.id, { tags, used });
          Modal.close();
          Toast.success('更新しました');
          await this._loadOdai();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
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
          this._imgCache.delete(odai.id);
          Toast.success('削除しました');
          await this._loadOdai();
        } catch (err) {
          Toast.error(err.message);
        }
      }
    );
  },
};
