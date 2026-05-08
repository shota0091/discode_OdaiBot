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

### 7. 最新コード（mainブランチ）を取得
```bash
cd ~/bots/discode_OdaiBot
git fetch origin
git checkout main
git reset --hard origin/main
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
DASHBOARD_BASE_URL=https://odaibot-dashboard.com
INVITE_EXPIRE_HOURS=1

# お題画像の保存先
ODAI_IMAGE_DIR=/data/odai

# バックアップ設定
BACKUP_DIR=/home/shota/backups/odaibot
BACKUP_KEEP_DAYS=7
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

### 11. テーブル作成（新規インストール）
```bash
cd ~/bots/discode_OdaiBot
source venv/bin/activate
python -m OdaiBotDB.setup_db
```

作成されるテーブル：`guild_settings`, `users`, `user_guilds`, `user_invites`, `odai`, `tags`, `odai_tags`, `odai_usage`, `channels`, `schedules`, `post_history`

### 11-alt. 既存DBのスキーマ更新（運用中のサーバーへの適用）

> users テーブルの構造変更（guild_id廃止 → user_guilds テーブルへ分離）が含まれる場合の手順。
> **ユーザーデータが少ない場合は users テーブルを DROP して再作成する方が確実。**

```bash
# MySQLに接続
mysql -u odaibot -p odai_bot
```

```sql
-- usersテーブルを削除（ユーザーは再登録が必要）
DROP TABLE IF EXISTS users;
EXIT;
```

```bash
# テーブル再作成（user_guilds も同時に作成される）
python -m OdaiBotDB.setup_db
```

その後、Dashboard ユーザーは `/odai_dashboard` コマンドで再招待して再登録する。

### 12. 画像保存ディレクトリの作成

お題画像はローカルファイルとして管理します（`ODAI_IMAGE_DIR` 配下）。

```bash
sudo mkdir -p /data/odai
sudo chown shota:shota /data/odai
```

### 13. お題画像の登録

**新規インストール時（JSONからの移行がない場合）:**
```bash
# ローカルPCから画像をサーバーへ転送
scp -r -i ~/.ssh/id_ed25519 ./images shota@133.18.120.136:/home/shota/bots/discode_OdaiBot/images

# サーバー上で一括登録（setup/ 配下のスクリプトを使用）
cd ~/bots/discode_OdaiBot
source venv/bin/activate
python setup/bulk_import_images.py --dry-run   # 確認
python setup/bulk_import_images.py             # 本番登録
```

**旧データ（JSON）からの移行がある場合:**
```bash
python setup/migrate_from_json.py
```
- `Data/{guild_id}_odai.json` と `templates/{guild_id}/` の画像をDBに移行
- 冪等実行可能（重複スキップ）

**既存 DB の画像を LONGBLOB → ローカルファイルへ移行する場合:**
```bash
python setup/migrate_odai_to_local.py
```
- DB の `data` カラム（LONGBLOB）から画像を読み出し、`ODAI_IMAGE_DIR/{guild_id}/filename` に書き出す
- 移行後は `data = NULL`、`storage_path = 実ファイルパス` に更新
- 冪等実行可能（既にファイルが存在する場合はスキップ）

### 14. バックアップの設定

```bash
# バックアップ保存先ディレクトリを作成
mkdir -p /home/shota/backups/odaibot

# 動作確認（手動実行）
bash /home/shota/bots/discode_OdaiBot/scripts/backup.sh

# cron 登録（毎日午前3時に自動実行）
crontab -e
```

crontab に以下を追加:
```
0 3 * * * /home/shota/bots/discode_OdaiBot/scripts/backup.sh >> /home/shota/backups/odaibot/backup.log 2>&1
```

バックアップ内容:
- `db.sql.gz` — MySQL ダンプ
- `images.tar.gz` — `ODAI_IMAGE_DIR` 配下の画像ファイル一式
- `BACKUP_KEEP_DAYS` 日超の古いバックアップは自動削除

---

## Phase 5: systemdサービス設定

### 15. odaibot.service 更新
```bash
sudo vi /etc/systemd/system/odaibot.service
```

変更箇所：
```ini
ExecStart=/home/shota/bots/discode_OdaiBot/venv/bin/python OdaiBot/odai_bot.py
```

### 16. odaibotapi.service 新規作成
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

### 17. サービス反映・起動
```bash
sudo systemctl daemon-reload
sudo systemctl enable odaibotapi
sudo systemctl start odaibotapi
sudo systemctl restart odaibot
```

---

## Phase 6: Nginx設定

### 18. Nginx設定ファイル作成
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

### 19. ディレクトリのパーミッション設定
nginxがhomeディレクトリにアクセスできるよう実行権限を付与：
```bash
chmod o+x /home/shota
chmod o+x /home/shota/bots
chmod o+x /home/shota/bots/discode_OdaiBot
chmod o+x /home/shota/bots/discode_OdaiBot/OdaiBotdashboard
sudo systemctl reload nginx
```

### 20. Nginx設定テスト・反映
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Phase 7: 自動デプロイ設定

### 21. update_odaibot.sh
```bash
vi ~/bots/update_odaibot.sh
```

```bash
#!/bin/bash
set -e

cd /home/shota/bots/discode_OdaiBot

echo "=== Pulling latest code ==="
git fetch origin
git reset --hard origin/main

echo "=== Updating venv packages ==="
source venv/bin/activate
pip install -r OdaiBot/requirements.txt || true
pip install -r OdaiBotAPI/requirements.txt || true

echo "=== Restarting services ==="
sudo systemctl restart odaibot
sudo systemctl restart odaibotapi

echo "=== Done ==="
```

sudoers設定（パスワードなしで systemctl restart を実行するため）：
```bash
sudo visudo -f /etc/sudoers.d/odaibot
```
```
shota ALL=(ALL) NOPASSWD: /bin/systemctl restart odaibot
shota ALL=(ALL) NOPASSWD: /bin/systemctl restart odaibotapi
```

### 22. GitHub Webhook設定
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
- Discord: `/odai_dashboard` コマンドで招待リンク発行（引数なしで実行者のDiscord名が使われる）
- 招待リンクをクリック → 初回はパスワード設定、2サーバー目以降は自動登録
- ログイン後、複数サーバーに所属していればサイドバーのドロップダウンで切り替え可能

---

## ユーザー管理

### Dashboard ユーザーの新規登録フロー
1. Discordで `/odai_dashboard` を実行（引数なし → 実行者のDiscord名が自動採用）
2. 任意で `role:user` を指定（デフォルト: admin）
3. 発行された招待リンクをDMで送付
4. ユーザーがリンクをクリック
   - **初回登録**: パスワード入力フォームが表示される
   - **他サーバーに登録済み**: パスワード入力不要、自動登録
5. ログイン後、所属する全サーバーがサイドバーのドロップダウンに表示される

### パスワードリセット（管理者操作）
Dashboard → ユーザー管理 → 対象ユーザーの「編集」→ 新しいパスワードを入力して保存

---

## 注意事項

- `.env` は `.gitignore` で除外済み。Gitにpushしないこと
- SSL証明書は90日ごとに自動更新される（certbotがcronで管理）
- mainブランチへのpushで自動デプロイが走る
- ユーザーはグローバル管理（`users` テーブル）＋サーバー別権限（`user_guilds` テーブル）で管理される
- ユーザー削除はそのサーバーとの紐付けのみ削除（他サーバーのデータは保持される）
