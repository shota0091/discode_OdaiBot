const API = {
  _token() { return localStorage.getItem('access_token'); },
  _guildId() { return localStorage.getItem('guild_id'); },
  _headers() {
    const h = { 'Content-Type': 'application/json' };
    if (this._token()) h['Authorization'] = `Bearer ${this._token()}`;
    return h;
  },
  async _fetch(path, options = {}) {
    const res = await fetch(`${CONFIG.API_BASE}${path}`, options);
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) {
      const msg = data.detail || data.error?.message || 'エラーが発生しました';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  },

  // Auth
  async loginGlobal(username, password) {
    return this._fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
  },
  async getGuilds() {
    return this._fetch('/api/auth/guilds', { headers: this._headers() });
  },
  async login(guildId, username, password) {
    return this._fetch(`/api/guilds/${guildId}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
  },
  async getInviteInfo(guildId, token) {
    return this._fetch(`/api/guilds/${guildId}/auth/invite-info?token=${encodeURIComponent(token)}`);
  },
  async register(guildId, inviteToken, password = null, displayName = null) {
    const body = { invite_token: inviteToken };
    if (password !== null) body.password = password;
    if (displayName !== null) body.display_name = displayName;
    return this._fetch(`/api/guilds/${guildId}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  },
  async resetPassword(guildId, inviteToken, password) {
    return this._fetch(`/api/guilds/${guildId}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ invite_token: inviteToken, password }),
    });
  },
  async getGuildName(guildId) {
    return this._fetch(`/api/guilds/${guildId}/settings/name`);
  },
  async getChannels() {
    return this._fetch(`/api/guilds/${this._guildId()}/settings/channels`, { headers: this._headers() });
  },
  async getInvites() {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/invites`, { headers: this._headers() });
  },
  async revokeInvite(inviteId) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/invites/${inviteId}`, {
      method: 'DELETE',
      headers: this._headers(),
    });
  },
  async createInvite(username, role) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/invite`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ username, role }),
    });
  },
  async getUsers() {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users`, { headers: this._headers() });
  },
  async createUser(username, password, role, displayName = null) {
    const body = { username, password, role };
    if (displayName) body.display_name = displayName;
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify(body),
    });
  },
  async updateUser(userId, data) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users/${userId}`, {
      method: 'PUT',
      headers: this._headers(),
      body: JSON.stringify(data),
    });
  },
  async deleteUser(userId) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users/${userId}`, {
      method: 'DELETE',
      headers: this._headers(),
    });
  },
  async unlockUser(userId) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users/${userId}/unlock`, {
      method: 'POST',
      headers: this._headers(),
    });
  },
  async getUserProfile(userId) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users/${userId}/profile`, { headers: this._headers() });
  },
  async getBans() {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/bans`, { headers: this._headers() });
  },
  async removeBan(banId) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/bans/${banId}`, {
      method: 'DELETE', headers: this._headers(),
    });
  },
  async banUser(userId) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users/${userId}/ban`, {
      method: 'POST', headers: this._headers(),
    });
  },
  async unbanUser(userId) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users/${userId}/unban`, {
      method: 'POST', headers: this._headers(),
    });
  },

  // Summary
  async getSummary() {
    return this._fetch(`/api/guilds/${this._guildId()}/dashboard-summary`, { headers: this._headers() });
  },

  // Plan
  async getPlan() {
    return this._fetch(`/api/guilds/${this._guildId()}/plan`);
  },

  // Free plan schedule
  async getPlanSchedule() {
    return this._fetch(`/api/guilds/${this._guildId()}/plan-schedule`, { headers: this._headers() });
  },
  async setPlanSchedule(channelId, time) {
    return this._fetch(`/api/guilds/${this._guildId()}/plan-schedule`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ channel_id: channelId, time }),
    });
  },
  async deletePlanSchedule(scheduleId) {
    return this._fetch(`/api/guilds/${this._guildId()}/plan-schedule/${scheduleId}`, {
      method: 'DELETE',
      headers: this._headers(),
    });
  },

  async expandCapacity(units, successUrl, cancelUrl) {
    return this._fetch(`/api/guilds/${this._guildId()}/plan/expand`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ units, success_url: successUrl, cancel_url: cancelUrl }),
    });
  },

  // Tags
  async getTags(q = '') {
    const qs = q ? `?q=${encodeURIComponent(q)}` : '';
    return this._fetch(`/api/guilds/${this._guildId()}/tags${qs}`, { headers: this._headers() });
  },
  async createTag(name, description) {
    return this._fetch(`/api/guilds/${this._guildId()}/tags`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ name, description }),
    });
  },
  async updateTag(tagId, data) {
    return this._fetch(`/api/guilds/${this._guildId()}/tags/${tagId}`, {
      method: 'PUT',
      headers: this._headers(),
      body: JSON.stringify(data),
    });
  },
  async deleteTag(tagId) {
    return this._fetch(`/api/guilds/${this._guildId()}/tags/${tagId}`, {
      method: 'DELETE',
      headers: this._headers(),
    });
  },
  async getTagDetail(tagId) {
    return this._fetch(`/api/guilds/${this._guildId()}/tags/${tagId}/detail`, { headers: this._headers() });
  },

  // Odai
  async getOdai(filename = '', tag = '', favorite = null) {
    const params = new URLSearchParams();
    if (filename) params.append('filename', filename);
    if (tag) params.append('tag', tag);
    if (favorite !== null) params.append('favorite', favorite);
    const qs = params.toString() ? `?${params}` : '';
    return this._fetch(`/api/guilds/${this._guildId()}/odai${qs}`, { headers: this._headers() });
  },
  async getOdaiUsage(odaiId) {
    return this._fetch(`/api/guilds/${this._guildId()}/odai/${odaiId}/usage`, { headers: this._headers() });
  },
  async getOdaiHistory(odaiId, page = 1, perPage = 5) {
    return this._fetch(
      `/api/guilds/${this._guildId()}/odai/${odaiId}/history?page=${page}&per_page=${perPage}`,
      { headers: this._headers() },
    );
  },
  async uploadOdai(formData) {
    return this._fetch(`/api/guilds/${this._guildId()}/odai`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this._token()}` },
      body: formData,
    });
  },
  async importOdai(formData) {
    return this._fetch(`/api/guilds/${this._guildId()}/odai/import`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this._token()}` },
      body: formData,
    });
  },
  async updateOdai(odaiId, data) {
    return this._fetch(`/api/guilds/${this._guildId()}/odai/${odaiId}`, {
      method: 'PUT',
      headers: this._headers(),
      body: JSON.stringify(data),
    });
  },
  async deleteOdai(odaiId) {
    return this._fetch(`/api/guilds/${this._guildId()}/odai/${odaiId}`, {
      method: 'DELETE',
      headers: this._headers(),
    });
  },
  async getOdaiImageUrl(odaiId) {
    const res = await fetch(`${CONFIG.API_BASE}/api/guilds/${this._guildId()}/odai/${odaiId}/image`, {
      headers: { 'Authorization': `Bearer ${this._token()}` },
    });
    if (!res.ok) throw new Error('画像の取得に失敗しました');
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },

  async testPost(channelId, tagMode = 'all', tagList = []) {
    return this._fetch(`/api/guilds/${this._guildId()}/test-post`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ channel_id: channelId, tag_mode: tagMode, tag_list: tagList }),
    });
  },

  // Schedules
  async getSchedules() {
    return this._fetch(`/api/guilds/${this._guildId()}/schedules`, { headers: this._headers() });
  },
  async createSchedule(data) {
    return this._fetch(`/api/guilds/${this._guildId()}/schedules`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify(data),
    });
  },
  async updateSchedule(scheduleId, data) {
    return this._fetch(`/api/guilds/${this._guildId()}/schedules/${scheduleId}`, {
      method: 'PUT',
      headers: this._headers(),
      body: JSON.stringify(data),
    });
  },
  async deleteSchedule(scheduleId) {
    return this._fetch(`/api/guilds/${this._guildId()}/schedules/${scheduleId}`, {
      method: 'DELETE',
      headers: this._headers(),
    });
  },

  // Settings
  async getSettings() {
    return this._fetch(`/api/guilds/${this._guildId()}/settings`, { headers: this._headers() });
  },
  async updateSettings(data) {
    return this._fetch(`/api/guilds/${this._guildId()}/settings`, {
      method: 'PUT',
      headers: this._headers(),
      body: JSON.stringify(data),
    });
  },
};
