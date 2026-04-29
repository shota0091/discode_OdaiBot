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
  async register(guildId, inviteToken, password = null) {
    const body = { invite_token: inviteToken };
    if (password !== null) body.password = password;
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
  async createUser(username, password, role) {
    return this._fetch(`/api/guilds/${this._guildId()}/auth/users`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ username, password, role }),
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

  // Summary
  async getSummary() {
    return this._fetch(`/api/guilds/${this._guildId()}/dashboard-summary`, { headers: this._headers() });
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

  // Odai
  async getOdai(filename = '', tag = '', used = null) {
    const params = new URLSearchParams();
    if (filename) params.append('filename', filename);
    if (tag) params.append('tag', tag);
    if (used !== null) params.append('used', used);
    const qs = params.toString() ? `?${params}` : '';
    return this._fetch(`/api/guilds/${this._guildId()}/odai${qs}`, { headers: this._headers() });
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
