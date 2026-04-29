# 本番環境デプロイ手順書

## 環境情報

| 項目 | 内容 |
|---|---|
| サーバー | カゴヤ VPS（Rocky Linux 9.6） |
| IP | 133.18.120.136 |
| ユーザー | shota |
| プロジェクトパス | `/home/shota/bots/discode_OdaiBot` |
| ドメイン | odaibot-dashboard.com |
| ドメイン登録 | XServerドメイン |
| DNS管理 | カゴヤ DNS |
| HTTPS | Let's Encrypt（Certbot + Nginx） |

---

## Phase 1: ドメイン・DNS設定

### 1. ドメイン取得
- XServerドメインで `odaibot-dashboard.com` を取得

### 2. XServerドメイン側のネームサーバー変更
XServerドメインの管理画面 → 「ネームサーバー設定変更」→「その他のネームサーバーを使用する」

```
ネームサーバー1: ns0.kagoya.net
ネームサーバー2: ns1.kagoya.net
```

### 3. カゴヤ DNS管理でAレコード追加
カゴヤ管理画面 → 「他社管理ドメイン登録」→ `odaibot-dashboard.com` を登録後、DNSレコード追加

| 種別 | ホスト名 | 値 |
|---|---|---|
| A | （空欄） | 133.18.120.136 |
| A | www | 133.18.120.136 |

DNS反映確認（数時間かかる場合あり）：
```bash
nslookup odaibot-dashboard.com 8.8.8.8
# 133.18.120.136 が返ればOK
```

---

## Phase 2: サーバー初期設定

### 4. Nginx インストール
```bash
sudo dnf install nginx -y
sudo systemctl enable --now nginx
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 5. Certbot インストール
```bash
sudo dnf install certbot python3-certbot-nginx -y
```

### 6. SSL証明書取得
```bash
sudo certbot --nginx -d odaibot-dashboard.com -d www.odaibot-dashboard.com
```
- メールアドレス入力
- 利用規約: Y
- 証明書は自動更新される（有効期限90日、cronで自動更新）

---

## Phase 3: コード展開

### 7. 新コード（devブランチ）を取得
```bash
cd ~/bots/discode_OdaiBot
git fetch origin
git checkout dev
git reset --hard origin/dev
```

### 8. Python依存パッケージインストール
```bash
source venv/bin/activate
# audioop-ltsはPython 3.12不要のため削除
sed -i '/audioop-lts/d' OdaiBot/requirements.txt
pip install -r OdaiBot/requirements.txt
pip install -r OdaiBotAPI/requirements.txt
```

### 9. .env ファイル作成
```bash
cp .env.example .env
vi .env
```

設定項目：
```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=odaibot
MYSQL_PASSWORD=（決めたパスワード）
MYSQL_DATABASE=odai_bot
DISCORD_BOT_TOKEN=（Discordトークン）
SECRET_KEY=（openssl rand -hex 32 で生成）
DASHBOARD_BASE_URL=https://odaibot-dashboard.com
INVITE_EXPIRE_HOURS=1
```

---

## Phase 4: データベース設定

### 10. MySQL専用ユーザー・DB作成
```bash
sudo mysql -u root -p
```

```sql
CREATE DATABASE IF NOT EXISTS odai_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'odaibot'@'localhost' IDENTIFIED BY 'パスワード';
GRANT ALL PRIVILEGES ON odai_bot.* TO 'odaibot'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 11. テーブル作成
```bash
cd ~/bots/discode_OdaiBot
source venv/bin/activate
python -m OdaiBotDB.setup_db
```

作成されるテーブル：`guild_settings`, `users`, `user_invites`, `odai`, `tags`, `odai_tags`, `odai_usage`, `channels`, `schedules`, `post_history`

### 12. 旧データ移行（JSONからMySQL）
```bash
python -m OdaiBotDB.migrate_from_json
```

- `Data/{guild_id}_odai.json` と `templates/{guild_id}/` の画像をDBに移行
- 冪等実行可能（重複スキップ）
- 画像が見つからない場合はDashboardから手動アップロード

---

## Phase 5: systemdサービス設定

### 13. odaibot.service 更新
```bash
sudo vi /etc/systemd/system/odaibot.service
```

変更箇所：
```ini
ExecStart=/home/shota/bots/discode_OdaiBot/venv/bin/python OdaiBot/odai_bot.py
```

### 14. odaibotapi.service 新規作成
```bash
sudo vi /etc/systemd/system/odaibotapi.service
```

```ini
[Unit]
Description=OdaiBotAPI FastAPI Server
After=network.target

[Service]
Type=simple
User=shota
WorkingDirectory=/home/shota/bots/discode_OdaiBot
ExecStart=/home/shota/bots/discode_OdaiBot/venv/bin/uvicorn OdaiBotAPI.api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
StartLimitInterval=0
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONIOENCODING=utf-8"

[Install]
WantedBy=multi-user.target
```

### 15. サービス反映・起動
```bash
sudo systemctl daemon-reload
sudo systemctl enable odaibotapi
sudo systemctl start odaibotapi
sudo systemctl restart odaibot
```

---

## Phase 6: Nginx設定

### 16. Nginx設定ファイル作成
```bash
sudo vi /etc/nginx/conf.d/odaibot.conf
```

```nginx
server {
    listen 80;
    server_name odaibot-dashboard.com www.odaibot-dashboard.com;

    location / {
        root /home/shota/bots/discode_OdaiBot/OdaiBotdashboard;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

※ Certbot実行後はHTTPS設定が自動追記される

### 17. ディレクトリのパーミッション設定
nginxがhomeディレクトリにアクセスできるよう実行権限を付与：
```bash
chmod o+x /home/shota
chmod o+x /home/shota/bots
chmod o+x /home/shota/bots/discode_OdaiBot
chmod o+x /home/shota/bots/discode_OdaiBot/OdaiBotdashboard
sudo systemctl reload nginx
```

### 18. Nginx設定テスト・反映
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Phase 7: 自動デプロイ設定

### 19. update_odaibot.sh 更新
```bash
vi ~/bots/update_odaibot.sh
```

```bash
#!/bin/bash
set -e

cd /home/shota/bots/discode_OdaiBot

echo "=== Pulling latest code ==="
git fetch origin
git reset --hard origin/dev

echo "=== Updating venv packages ==="
source venv/bin/activate
pip install -r OdaiBot/requirements.txt || true
pip install -r OdaiBotAPI/requirements.txt || true

echo "=== Restarting services ==="
sudo systemctl restart odaibot
sudo systemctl restart odaibotapi

echo "=== Done ==="
```

### 20. GitHub Webhook設定
GitHub リポジトリ → Settings → Webhooks → Add webhook

| 項目 | 値 |
|---|---|
| Payload URL | `http://133.18.120.136:9000/github-webhook` |
| Content type | `application/json` |
| Which events | Just the push event |

ファイアウォール確認：
```bash
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

---

## 動作確認

```bash
# サービス状態確認
sudo systemctl status odaibot odaibotapi

# ログ確認
sudo journalctl -u odaibot -f
sudo journalctl -u odaibotapi -f

# API疎通確認
curl https://odaibot-dashboard.com/api/guilds/{guild_id}/settings/name
```

- Dashboard: https://odaibot-dashboard.com にアクセス
- Discord: `/odai_dashboard` コマンドで招待リンク発行 → ユーザー登録 → ログイン

---

## 注意事項

- `.env` は `.gitignore` で除外済み。Gitにpushしないこと
- SSL証明書は90日ごとに自動更新される（certbotがcronで管理）
- devブランチへのpushで自動デプロイが走る
- 本番切り替え後は `update_odaibot.sh` の `origin/dev` を `origin/main` に変更すること
