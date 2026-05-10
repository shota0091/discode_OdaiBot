const PlanPage = {
  render() {
    return Layout.render('プラン', `<div id="plan-root"><p class="loading">読み込み中...</p></div>`);
  },

  async init() {
    Layout.bindLogout();
    const isAdmin = localStorage.getItem('role') === 'admin';
    const storedPlanName = localStorage.getItem('plan_name') || 'free';
    const isFree = storedPlanName === 'free';

    try {
      const [planRes, summaryRes, settingsRes] =
        await Promise.all([API.getPlan(), API.getSummary(), API.getSettings()]);

      const p = planRes.data;
      const odaiCount = summaryRes.data.odai_count ?? 0;
      const useDefault = settingsRes.data.use_default_odai;

      const planLabels = { free: 'Free', light: 'Light', pro: 'Pro', enterprise: 'Enterprise' };
      const planColors = { free: 'disabled', light: 'info', pro: 'primary', enterprise: 'success' };
      const statusLabels = { active: '有効', canceled: 'キャンセル済み', past_due: '支払い遅延' };
      const statusColors = { active: 'success', canceled: 'error', past_due: 'warning' };

      const planName = p.plan_name || 'free';
      const isPro = planName === 'pro';  // pro のみ。enterprise は対象外
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
            </tbody>
          </table>
        </div>


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
              <div class="capacity-bar-wrap">
                <div class="capacity-bar">
                  <div class="capacity-bar__fill capacity-bar__fill--${capBarClass}" style="width: ${capPercent}%"></div>
                </div>
                <span class="capacity-bar__percent">${capPercent}%</span>
              </div>
              <p class="capacity-info__sub">${capTotal - odaiCount} 件追加可能</p>
              ` : `
              <p class="capacity-info__sub">容量制限なし</p>
              `}
            </div>
            ${p.can_expand_capacity && isAdmin && capTotal !== null ? `
            <div class="expand-action">
              <button class="btn btn--primary btn--sm" id="expand-btn">容量を拡張する</button>
              <p class="text-muted" style="margin-top:6px;font-size:12px">+100件単位で拡張できます</p>
            </div>
            ` : ''}
          `}
        </div>
        ` : ''}

        ${isPro ? `
        <div class="section">
          <h2 class="section__title">デフォルトお題設定</h2>
          ${isAdmin ? `
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
        ` : ''}

        ${isAdmin && planName !== 'enterprise' ? `
        <div class="section">
          <h2 class="section__title">プランを変更する</h2>
          <div class="plan-change-list">
            ${planName !== 'light' ? `
            <div class="plan-change-item">
              <div>
                <strong>Light</strong> <span class="text-muted">¥600/月</span>
                <p class="text-muted" style="font-size:12px;margin-top:2px">独自お題100件・スケジュール自由設定</p>
              </div>
              <button class="btn btn--secondary btn--sm" data-plan="light">変更する</button>
            </div>
            ` : ''}
            ${planName !== 'pro' ? `
            <div class="plan-change-item">
              <div>
                <strong>Pro</strong> <span class="text-muted">¥960/月</span>
                <p class="text-muted" style="font-size:12px;margin-top:2px">独自お題1000件・タグ機能</p>
              </div>
              <button class="btn btn--primary btn--sm" data-plan="pro">変更する</button>
            </div>
            ` : ''}
          </div>
        </div>
        ` : ''}

        ${isAdmin && planName !== 'free' && planName !== 'enterprise' && p.status === 'active' ? `
        <div class="section">
          <h2 class="section__title">解約</h2>
          <p class="text-muted" style="margin-bottom:12px">解約後も現在の請求期間終了日までご利用いただけます。</p>
          <button class="btn btn--danger btn--sm" id="cancel-plan-btn">解約する</button>
        </div>
        ` : ''}
      `;

      if (isAdmin && p.can_expand_capacity) this._bindExpandButton();
      if (isAdmin && isPro) this._bindDefaultOdaiForm();
      if (isAdmin && planName !== 'free' && planName !== 'enterprise' && p.status === 'active') this._bindCancelButton();
      if (isAdmin && planName !== 'enterprise') this._bindPlanChangeButtons();
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

  _bindExpandButton() {
    const btn = document.getElementById('expand-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const modal = document.createElement('div');
      modal.className = 'modal-overlay';
      modal.innerHTML = `
        <div class="modal">
          <div class="modal__header">
            <span class="modal__title">容量拡張</span>
          </div>
          <div class="modal__body">
            <p class="text-muted" style="margin-bottom:12px">1単位 = +100件。拡張後は Stripe の決済ページに移動します。</p>
            <div class="form__group">
              <label class="form__label">拡張単位数</label>
              <input type="number" id="expand-units" class="form__input" value="1" min="1" max="10" style="width:80px">
            </div>
            <div id="expand-error" class="form__error" hidden></div>
          </div>
          <div class="modal__footer">
            <button class="btn btn--secondary" id="expand-cancel-btn">キャンセル</button>
            <button class="btn btn--primary" id="expand-confirm-btn">決済へ進む</button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      document.getElementById('expand-cancel-btn').addEventListener('click', () => modal.remove());
      document.getElementById('expand-confirm-btn').addEventListener('click', async () => {
        const units = parseInt(document.getElementById('expand-units').value, 10);
        const errorEl = document.getElementById('expand-error');
        errorEl.hidden = true;
        if (!units || units < 1) {
          errorEl.textContent = '1以上の数値を入力してください';
          errorEl.hidden = false;
          return;
        }
        const confirmBtn = document.getElementById('expand-confirm-btn');
        confirmBtn.disabled = true;
        try {
          const origin = location.origin + location.pathname;
          const res = await API.expandCapacity(units, `${origin}#plan`, `${origin}#plan`);
          location.href = res.url;
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
          confirmBtn.disabled = false;
        }
      });
    });
  },

  _bindPlanChangeButtons() {
    document.querySelectorAll('[data-plan]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const plan = btn.dataset.plan;
        const label = plan === 'light' ? 'Light (¥600/月)' : 'Pro (¥960/月)';
        Modal.confirm(
          'プラン変更',
          `<strong>${label}</strong> に変更しますか？<br>Stripe の決済ページに移動します。`,
          async () => {
            try {
              const origin = location.origin + location.pathname;
              const res = await API.subscribePlan(plan, `${origin}#plan`, `${origin}#plan`);
              location.href = res.url;
            } catch (err) {
              Toast.error(err.message);
            }
          }
        );
      });
    });
  },

  _bindCancelButton() {
    const btn = document.getElementById('cancel-plan-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      Modal.confirm(
        '解約確認',
        '本当に解約しますか？<br>解約後も現在の請求期間終了日までご利用いただけます。',
        async () => {
          try {
            await API.cancelPlan();
            Toast.success('解約しました。期間終了日までご利用いただけます。');
            Router.navigate(location.hash);
          } catch (err) {
            Toast.error(err.message);
          }
        }
      );
    });
  },

};
