const PlanPage = {
  render() {
    return Layout.render('プラン', `<div id="plan-root"><p class="loading">読み込み中...</p></div>`);
  },

  async init() {
    Layout.bindLogout();
    const isAdmin = localStorage.getItem('role') === 'admin';
    const storedPlanName = localStorage.getItem('plan_name') || 'free';
    const isFree = storedPlanName === 'free';
    const isPro = storedPlanName === 'pro' || storedPlanName === 'enterprise';

    try {
      const baseReqs = [API.getPlan(), API.getSummary(), API.getSettings()];
      const extraReqs = isFree
        ? [API.getPlanSchedule(), API.getChannels()]
        : [Promise.resolve(null), Promise.resolve(null)];

      const [planRes, summaryRes, settingsRes, scheduleRes, channelsRes] =
        await Promise.all([...baseReqs, ...extraReqs]);

      const p = planRes.data;
      const odaiCount = summaryRes.data.odai_count ?? 0;
      const useDefault = settingsRes.data.use_default_odai;
      const schedule = scheduleRes?.data ?? null;
      const channels = channelsRes?.data ?? [];

      const planLabels = { free: 'Free', light: 'Light', pro: 'Pro', enterprise: 'Enterprise' };
      const planColors = { free: 'disabled', light: 'info', pro: 'primary', enterprise: 'success' };
      const statusLabels = { active: '有効', canceled: 'キャンセル済み', past_due: '支払い遅延' };
      const statusColors = { active: 'success', canceled: 'error', past_due: 'warning' };

      const planName = p.plan_name || 'free';
      const planLabel = planLabels[planName] || planName;
      const planColor = planColors[planName] || 'disabled';
      const statusLabel = statusLabels[p.status] || p.status || '有効';
      const statusColor = statusColors[p.status] || 'success';

      const capTotal = p.custom_odai_capacity === null ? null : (p.custom_odai_capacity ?? 0);
      const capDisplay = capTotal === null ? '∞' : String(capTotal);
      const capPercent = capTotal === null || capTotal === 0 ? 0 : Math.min(100, Math.round(odaiCount / capTotal * 100));
      const capBarClass = capPercent >= 90 ? 'danger' : capPercent >= 70 ? 'warning' : 'normal';

      document.getElementById('plan-root').innerHTML = `
        <div class="section">
          <h2 class="section__title">現在のプラン</h2>
          <table class="table table--info">
            <tbody>
              <tr>
                <th>プラン</th>
                <td><span class="badge badge--${planColor}">${escapeHtml(planLabel)}</span></td>
              </tr>
              <tr>
                <th>月額</th>
                <td>${p.price === 0 ? '無料' : `¥${Number(p.price).toLocaleString()}`}</td>
              </tr>
              <tr>
                <th>ステータス</th>
                <td><span class="badge badge--${statusColor}">${escapeHtml(statusLabel)}</span></td>
              </tr>
              ${p.current_period_end ? `
              <tr>
                <th>次回更新日</th>
                <td>${formatDate(p.current_period_end)}</td>
              </tr>
              ` : ''}
              <tr>
                <th>Discord 操作</th>
                <td>${p.has_discord_op ? '<span class="badge badge--success">有効</span>' : '<span class="badge badge--disabled">無効</span>'}</td>
              </tr>
            </tbody>
          </table>
        </div>

        ${isFree ? `
        <div class="section" id="schedule-section">
          <h2 class="section__title">投稿スケジュール</h2>
          <p class="text-muted" style="margin-bottom:12px">デフォルトお題の自動投稿スケジュールを1件設定できます。</p>
          ${isAdmin ? `
          <form id="schedule-form" class="form form--inline">
            <div class="form__group">
              <label class="form__label">チャンネル</label>
              <select id="sch-channel" class="form__select">
                <option value="">-- 選択 --</option>
                ${channels.map(c => `<option value="${escapeHtml(c.channel_id)}" ${schedule && String(schedule.channel_id) === String(c.channel_id) ? 'selected' : ''}>${escapeHtml(c.name)}</option>`).join('')}
              </select>
            </div>
            <div class="form__group">
              <label class="form__label">時刻</label>
              <input type="time" id="sch-time" class="form__input" value="${schedule ? escapeHtml(schedule.time) : '08:00'}">
            </div>
            <div id="sch-error" class="form__error" hidden></div>
            <div class="form__actions">
              <button type="submit" class="btn btn--primary" id="sch-save-btn">保存</button>
              ${schedule ? `<button type="button" class="btn btn--danger btn--sm" id="sch-delete-btn">削除</button>` : ''}
            </div>
          </form>
          ` : `
          ${schedule ? `
          <table class="table table--info">
            <tbody>
              <tr><th>チャンネル</th><td>${escapeHtml(channels.find(c => String(c.channel_id) === String(schedule.channel_id))?.name || schedule.channel_id)}</td></tr>
              <tr><th>時刻</th><td>${escapeHtml(schedule.time)}</td></tr>
              <tr><th>状態</th><td><span class="badge badge--${schedule.enabled ? 'success' : 'disabled'}">${schedule.enabled ? '有効' : '無効'}</span></td></tr>
            </tbody>
          </table>
          ` : '<p class="text-muted">スケジュールは未設定です。管理者に設定を依頼してください。</p>'}
          `}
        </div>
        ` : ''}

        ${!isFree ? `
        <div class="section">
          <h2 class="section__title">独自お題容量</h2>
          ${capTotal === 0 ? `
            <p class="text-muted">このプランでは独自お題を登録できません。</p>
          ` : `
            <div class="capacity-info">
              <div class="capacity-info__label">
                <span class="capacity-info__used">${odaiCount} 件使用中</span>
                <span class="capacity-info__total">/ ${capDisplay} 件</span>
              </div>
              ${capTotal !== null ? `
              <div class="capacity-bar">
                <div class="capacity-bar__fill capacity-bar__fill--${capBarClass}" style="width: ${capPercent}%"></div>
              </div>
              <p class="capacity-info__sub">${capTotal - odaiCount} 件追加可能</p>
              ` : `
              <p class="capacity-info__sub">容量制限なし</p>
              `}
            </div>
            ${p.can_expand_capacity ? `<p class="text-muted plan-expand-hint">容量拡張は Discord コマンド <code>/expand</code> から行えます。</p>` : ''}
          `}
        </div>
        ` : ''}

        <div class="section">
          <h2 class="section__title">デフォルトお題設定</h2>
          ${isAdmin && isPro ? `
          <form id="default-odai-form" class="form form--inline">
            <div class="form__group">
              <label class="form__label">デフォルトお題を使用する</label>
              <select id="use-default-odai" class="form__select">
                <option value="true" ${useDefault ? 'selected' : ''}>ON</option>
                <option value="false" ${!useDefault ? 'selected' : ''}>OFF</option>
              </select>
            </div>
            <div id="default-odai-error" class="form__error" hidden></div>
            <button type="submit" class="btn btn--primary" id="default-odai-save-btn">保存</button>
          </form>
          ` : `
          <table class="table table--info">
            <tbody>
              <tr>
                <th>デフォルトお題</th>
                <td><span class="badge badge--${useDefault ? 'success' : 'disabled'}">${useDefault ? 'ON' : 'OFF'}</span></td>
              </tr>
            </tbody>
          </table>
          `}
        </div>
      `;

      if (isAdmin && isPro) this._bindDefaultOdaiForm();
      if (isAdmin && isFree) this._bindScheduleForm(schedule);
    } catch (err) {
      document.getElementById('plan-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },

  _bindDefaultOdaiForm() {
    const form = document.getElementById('default-odai-form');
    if (!form) return;
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const errorEl = document.getElementById('default-odai-error');
      errorEl.hidden = true;
      const btn = document.getElementById('default-odai-save-btn');
      btn.disabled = true;
      try {
        const use_default_odai = document.getElementById('use-default-odai').value === 'true';
        await API.updateSettings({ use_default_odai });
        Toast.success('設定を保存しました');
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
      } finally {
        btn.disabled = false;
      }
    });
  },

  _bindScheduleForm(schedule) {
    const form = document.getElementById('schedule-form');
    if (!form) return;

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const errorEl = document.getElementById('sch-error');
      errorEl.hidden = true;
      const btn = document.getElementById('sch-save-btn');
      btn.disabled = true;
      try {
        const channelId = document.getElementById('sch-channel').value;
        const time = document.getElementById('sch-time').value;
        if (!channelId) throw new Error('チャンネルを選択してください');
        await API.setPlanSchedule(channelId, time);
        Toast.success('スケジュールを保存しました');
        Router.navigate(location.hash);
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
      } finally {
        btn.disabled = false;
      }
    });

    const deleteBtn = document.getElementById('sch-delete-btn');
    if (deleteBtn && schedule) {
      deleteBtn.addEventListener('click', async () => {
        if (!confirm('スケジュールを削除しますか？')) return;
        try {
          await API.deletePlanSchedule(schedule.id);
          Toast.success('スケジュールを削除しました');
          Router.navigate(location.hash);
        } catch (err) {
          Toast.error(err.message);
        }
      });
    }
  },
};
