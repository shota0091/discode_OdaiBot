const SchedulesPage = {
  _schedules: [],
  _allTags: [],
  _allChannels: [],

  render() {
    return Layout.render('スケジュール管理', `
      <div class="page-actions">
        <button class="btn btn--primary" id="create-schedule-btn">＋ スケジュール追加</button>
      </div>
      <div id="schedules-table-root"><p class="loading">読み込み中...</p></div>
    `);
  },

  async init() {
    Layout.bindLogout();
    try {
      const res = await API.getTags();
      this._allTags = res.data;
    } catch (_) {}
    try {
      const res = await API.getChannels();
      this._allChannels = res.data;
    } catch (_) {}
    document.getElementById('create-schedule-btn').addEventListener('click', () => this._openForm());
    await this._loadSchedules();
  },

  async _loadSchedules() {
    try {
      const res = await API.getSchedules();
      this._schedules = res.data;
      this._renderTable();
    } catch (err) {
      document.getElementById('schedules-table-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _renderTable() {
    if (!this._schedules.length) {
      document.getElementById('schedules-table-root').innerHTML = '<p class="text-muted">スケジュールが登録されていません。</p>';
      return;
    }
    document.getElementById('schedules-table-root').innerHTML = `
      <div class="table-scroll">
      <table class="table">
        <thead>
          <tr><th class="hide-mobile">ID</th><th>チャンネル</th><th>時刻</th><th>有効</th><th>タグモード</th><th class="hide-mobile">タグリスト</th><th>操作</th></tr>
        </thead>
        <tbody>
          ${this._schedules.map(s => `
            <tr>
              <td class="hide-mobile">${s.id}</td>
              <td>
                ${s.channel_name ? `<span>${escapeHtml(s.channel_name)}</span><br><code style="font-size:11px;color:var(--text-muted)">${s.channel_id}</code>` : `<code>${s.channel_id}</code>`}
              </td>
              <td>${escapeHtml(s.time)}</td>
              <td>
                <span class="badge badge--${s.enabled ? 'success' : 'disabled'}">${s.enabled ? 'ON' : 'OFF'}</span>
              </td>
              <td><span class="badge badge--mode">${s.tag_mode}</span></td>
              <td class="hide-mobile">${(s.tag_list || []).map(t => `<span class="tag-chip">${escapeHtml(t)}</span>`).join(' ') || '-'}</td>
              <td class="table__actions">
                <button class="btn btn--sm btn--${s.enabled ? 'warning' : 'success'}" data-toggle="${s.id}">${s.enabled ? '無効化' : '有効化'}</button>
                <button class="btn btn--sm btn--secondary" data-edit="${s.id}">編集</button>
                <button class="btn btn--sm btn--danger" data-delete="${s.id}">削除</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      </div>
    `;
    document.querySelectorAll('[data-toggle]').forEach(btn => {
      const item = this._schedules.find(s => s.id === parseInt(btn.dataset.toggle));
      btn.addEventListener('click', () => this._toggleEnabled(item));
    });
    document.querySelectorAll('[data-edit]').forEach(btn => {
      const item = this._schedules.find(s => s.id === parseInt(btn.dataset.edit));
      btn.addEventListener('click', () => this._openForm(item));
    });
    document.querySelectorAll('[data-delete]').forEach(btn => {
      const item = this._schedules.find(s => s.id === parseInt(btn.dataset.delete));
      btn.addEventListener('click', () => this._confirmDelete(item));
    });
  },

  async _toggleEnabled(schedule) {
    try {
      await API.updateSchedule(schedule.id, {
        channel_id: schedule.channel_id,
        time: schedule.time,
        enabled: !schedule.enabled,
        tag_mode: schedule.tag_mode,
        tag_list: schedule.tag_list,
      });
      Toast.success(schedule.enabled ? '無効化しました' : '有効化しました');
      await this._loadSchedules();
    } catch (err) {
      Toast.error(err.message);
    }
  },

  _channelDisplayValue(channelId) {
    if (!channelId) return '';
    const ch = this._allChannels.find(c => c.channel_id === channelId);
    return ch?.name ? `#${ch.name}` : channelId;
  },

  _resolveChannelId(input) {
    const trimmed = input.trim();
    if (trimmed.startsWith('#')) {
      const name = trimmed.slice(1);
      const found = this._allChannels.find(c => c.name === name);
      return found ? found.channel_id : '';
    }
    return trimmed;
  },

  _openForm(schedule = null) {
    const title = schedule ? 'スケジュール編集' : 'スケジュール追加';
    const tagOptions = this._allTags.map(t =>
      `<option value="${escapeHtml(t.name)}" ${(schedule?.tag_list || []).includes(t.name) ? 'selected' : ''}>${escapeHtml(t.name)}</option>`
    ).join('');
    const datalistOptions = this._allChannels.map(c =>
      `<option value="#${escapeHtml(c.name || c.channel_id)}"></option>`
    ).join('');
    const channelValue = this._channelDisplayValue(schedule?.channel_id || '');
    const body = `
      <div class="form">
        <div class="form__group">
          <label class="form__label">チャンネル <span class="required">*</span></label>
          <input type="text" id="f-channel" class="form__input" list="channel-datalist"
            value="${escapeHtml(channelValue)}" placeholder="チャンネルを選択またはIDを入力" required autocomplete="off">
          <datalist id="channel-datalist">${datalistOptions}</datalist>
          <small class="form__hint">一覧から選択するか、チャンネルIDを直接入力できます</small>
        </div>
        <div class="form__group">
          <label class="form__label">投稿時刻 <span class="required">*</span></label>
          <input type="time" id="f-time" class="form__input" value="${schedule?.time || '09:00'}" required>
        </div>
        <div class="form__group">
          <label class="form__label">有効</label>
          <select id="f-enabled" class="form__select">
            <option value="true" ${schedule === null || schedule?.enabled ? 'selected' : ''}>ON</option>
            <option value="false" ${schedule && !schedule.enabled ? 'selected' : ''}>OFF</option>
          </select>
        </div>
        <div class="form__group">
          <label class="form__label">タグモード <span class="required">*</span></label>
          <select id="f-tag-mode" class="form__select">
            <option value="all" ${(schedule?.tag_mode || 'all') === 'all' ? 'selected' : ''}>all（全てのタグ）</option>
            <option value="allow" ${schedule?.tag_mode === 'allow' ? 'selected' : ''}>allow（許可タグのみ）</option>
            <option value="deny" ${schedule?.tag_mode === 'deny' ? 'selected' : ''}>deny（除外タグを指定）</option>
          </select>
        </div>
        <div class="form__group" id="f-tag-list-group" ${(schedule?.tag_mode || 'all') === 'all' ? 'style="display:none"' : ''}>
          <label class="form__label">タグリスト</label>
          <select id="f-tag-list" class="form__select" multiple size="4">${tagOptions}</select>
        </div>
        <div id="f-error" class="form__error" hidden></div>
      </div>
    `;
    Modal.show(title, body, {
      onOpen: () => {
        document.getElementById('f-tag-mode').addEventListener('change', e => {
          document.getElementById('f-tag-list-group').style.display = e.target.value === 'all' ? 'none' : '';
        });
      },
      onConfirm: async () => {
        const errorEl = document.getElementById('f-error');
        errorEl.hidden = true;
        const channel_id = this._resolveChannelId(document.getElementById('f-channel').value);
        const time = document.getElementById('f-time').value;
        const enabled = document.getElementById('f-enabled').value === 'true';
        const tag_mode = document.getElementById('f-tag-mode').value;
        const tag_list = Array.from(document.getElementById('f-tag-list').selectedOptions).map(o => o.value);

        if (!channel_id || !/^\d+$/.test(channel_id)) { errorEl.textContent = 'チャンネルを選択するか、チャンネルIDを数字で入力してください'; errorEl.hidden = false; return; }
        if (!time) { errorEl.textContent = '投稿時刻を入力してください'; errorEl.hidden = false; return; }
        if (tag_mode !== 'all' && !tag_list.length) {
          errorEl.textContent = `tag_mode が ${tag_mode} の場合はタグリストを1件以上選択してください`;
          errorEl.hidden = false;
          return;
        }

        try {
          const data = { channel_id, time, enabled, tag_mode, tag_list };
          if (schedule) {
            await API.updateSchedule(schedule.id, data);
          } else {
            await API.createSchedule(data);
          }
          Modal.close();
          Toast.success(schedule ? '更新しました' : '追加しました');
          await this._loadSchedules();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      },
    });
  },

  _confirmDelete(schedule) {
    Modal.confirm(
      'スケジュール削除',
      `ID: ${schedule.id}（${schedule.channel_id} / ${schedule.time}）のスケジュールを削除しますか？`,
      async () => {
        try {
          await API.deleteSchedule(schedule.id);
          Toast.success('削除しました');
          await this._loadSchedules();
        } catch (err) {
          Toast.error(err.message);
        }
      }
    );
  },
};
