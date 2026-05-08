# デプロイ TODO リスト

## 環境情報

| 項目 | 内容 |
|---|---|
| サーバー | カゴヤ VPS（Rocky Linux 9.6） |
| IP | 133.18.120.136 |
| ユーザー | shota |
| プロジェクトパス | `/home/shota/bots/discode_OdaiBot` |
| HTTPS | Cloudflare Tunnel（ドメイン不要・無料） |

---

## TODO

### Phase 1: サーバー準備

- [ ] **1. 新コードをサーバーに展開**
  ```bash
  cd ~/bots/discode_OdaiBot
  git fetch origin
  git checkout dev
  git pull origin dev
  ```

- [ ] **2. Python 依存パッケージインストール**
  ```bash
  source venv/bin/activate
  pip install -r OdaiBot/requirements.txt
  pip install -r OdaiBotAPI/requirements.txt
  ```

- [ ] **3. .env ファイル作成（本番用）**
  ```bash
  cp .env.example .env
  vi .env  # 各値を本番用に設定
  ```
  設定が必要な項目：
  - `DISCORD_BOT_TOKEN`
  - `MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE`
  - `SECRET_KEY`
  - `DASHBOARD_BASE_URL`（Cloudflare Tunnel の URL が決まってから設定）

---

### Phase 2: DB セットアップ・データ移行

- [ ] **4. DB テーブル作成**
  ```bash
  python -m OdaiBotDB.setup_db
  ```

- [ ] **5. 旧 JSON データ移行**
  ```bash
  # Data/ と templates/ が ~/bots/discode_OdaiBot 配下にあることを確認してから実行
  python -m OdaiBotDB.migrate_from_json
  ```

---

### Phase 3: systemd サービス設定

- [ ] **6. odaibot.service 更新**（新パスに変更）
  ```bash
  sudo vi /etc/systemd/system/odaibot.service
  ```
  変更点：
  - `ExecStart` → `venv/bin/python OdaiBot/odai_bot.py`
  - `WorkingDirectory` → `/home/shota/bots/discode_OdaiBot`

- [ ] **7. odaibotapi.service 新規作成**
  ```bash
  sudo vi /etc/systemd/system/odaibotapi.service
  ```

- [ ] **8. サービス反映・起動**
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable odaibotapi
  sudo systemctl start odaibotapi
  sudo systemctl restart odaibot
  ```

---

### Phase 4: Cloudflare Tunnel 設定

- [ ] **9. cloudflared インストール**
  ```bash
  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.rpm -o cloudflared.rpm
  sudo rpm -ivh cloudflared.rpm
  ```

- [ ] **10. Cloudflare アカウント作成**（未取得の場合）
  - cloudflare.com でアカウント登録

- [ ] **11. Tunnel 作成・設定**
  ```bash
  cloudflared tunnel login
  cloudflared tunnel create odai-dashboard
  cloudflared tunnel route dns odai-dashboard <your-subdomain>
  ```

- [ ] **12. cloudflared サービス化**
  ```bash
  sudo cloudflared service install
  sudo systemctl enable cloudflared
  sudo systemctl start cloudflared
  ```

- [ ] **13. .env の DASHBOARD_BASE_URL を更新**
  - Tunnel の URL が確定したら設定
  - API サービス再起動

---

### Phase 5: 自動デプロイ設定

- [ ] **14. update_odaibot.sh を新構成に更新**
  - `git pull origin dev`（dev ブランチから取得）
  - API サービスの再起動を追加

- [ ] **15. GitHub Webhook 確認・修正**
  - `discord-bot-auto-update` サービスが正常動作しているか確認
  - Webhook のエンドポイント URL を確認

- [ ] **16. GitHub に Webhook 設定**
  - リポジトリ Settings → Webhooks
  - `dev` ブランチへの push でトリガー

---

### Phase 6: 動作確認

- [ ] **17. Bot 動作確認**
  - Discord で `/ping` コマンド
  - `/odai` コマンドでお題投稿
  - スケジュール投稿

- [ ] **18. Dashboard 動作確認**
  - HTTPS でアクセスできるか
  - ログイン
  - お題管理・スケジュール管理

- [ ] **19. 自動デプロイ確認**
  - dev ブランチに push → 自動反映されるか

---

### Phase 7: 本番切り替え（動作確認後）

- [ ] **20. dev → main へ PR・マージ**
  - GitHub でプルリクエスト作成
  - 動作確認済みを確認してマージ

- [ ] **21. update_odaibot.sh を main ブランチに変更**

---

## 参考コマンド

```bash
# サービス状態確認
sudo systemctl status odaibot odaibotapi

# ログ確認
sudo journalctl -u odaibot -f
sudo journalctl -u odaibotapi -f

# サービス再起動
sudo systemctl restart odaibot odaibotapi
```
