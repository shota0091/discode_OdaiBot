const DashboardPage = {
  render() {
    return Layout.render('ダッシュボード', `<div id="summary-root"><p class="loading">読み込み中...</p></div>`);
  },
  async init() {
    Layout.bindLogout();
    try {
      const res = await API.getSummary();
      const s = res.data;
      const recentPosts = s.recent_posts || [];
      const recentPostsHTML = recentPosts.length
        ? `<table class="table">
            <thead>
              <tr><th>ファイル名</th><th>チャンネル</th><th>結果</th><th>投稿日時</th></tr>
            </thead>
            <tbody>
              ${recentPosts.map(p => `
              <tr>
                <td>${escapeHtml(p.filename)}</td>
                <td>${escapeHtml(p.channel_name || p.channel_id)}</td>
                <td><span class="badge badge--${p.result === 'success' ? 'success' : 'error'}">${p.result}</span></td>
                <td>${formatDate(p.posted_at)}</td>
              </tr>`).join('')}
            </tbody>
          </table>`
        : '<p class="text-muted">投稿履歴はまだありません</p>';

      document.getElementById('summary-root').innerHTML = `
        <div class="summary-grid">
          <div class="summary-card">
            <div class="summary-card__value">${s.odai_count}</div>
            <div class="summary-card__label">登録お題数</div>
          </div>
          <div class="summary-card">
            <div class="summary-card__value">${s.active_schedule_count}</div>
            <div class="summary-card__label">有効スケジュール数</div>
          </div>
          <div class="summary-card">
            <div class="summary-card__value">${s.channel_count}</div>
            <div class="summary-card__label">投稿先チャンネル数</div>
          </div>
        </div>
        <div class="section">
          <h2 class="section__title">直近の投稿</h2>
          ${recentPostsHTML}
        </div>
        <div class="section">
          <h2 class="section__title">クイックリンク</h2>
          <div class="quick-links">
            <a href="#/dashboard/odai" class="quick-link">🖼️ お題管理</a>
            <a href="#/dashboard/tags" class="quick-link">🏷️ タグ管理</a>
            <a href="#/dashboard/schedules" class="quick-link">📅 スケジュール管理</a>
            <a href="#/dashboard/settings" class="quick-link">⚙️ 設定</a>
          </div>
        </div>
      `;
    } catch (err) {
      document.getElementById('summary-root').innerHTML = `<p class="text-error">${escapeHtml(err.message)}</p>`;
    }
  },
};
