#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

# .env から変数を読み込む
if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        export "$line" 2>/dev/null || true
    done < "$ENV_FILE"
fi

BACKUP_DIR="${BACKUP_DIR:-/home/shota/backups/odaibot}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
IMAGE_DIR="${ODAI_IMAGE_DIR:-/data/odai}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEST="$BACKUP_DIR/$TIMESTAMP"

mkdir -p "$DEST"
echo "[$TIMESTAMP] バックアップ開始"

# DB ダンプ
mysqldump \
    -h "${MYSQL_HOST:-127.0.0.1}" \
    -P "${MYSQL_PORT:-3306}" \
    -u "${MYSQL_USER:-root}" \
    -p"${MYSQL_PASSWORD:-}" \
    "${MYSQL_DATABASE:-odai_bot}" \
    | gzip > "$DEST/db.sql.gz"
echo "  DB ダンプ完了"

# 画像ファイルのアーカイブ
if [ -d "$IMAGE_DIR" ]; then
    tar -czf "$DEST/images.tar.gz" -C "$(dirname "$IMAGE_DIR")" "$(basename "$IMAGE_DIR")"
    echo "  画像アーカイブ完了"
else
    echo "  [WARN] 画像ディレクトリが見つかりません: $IMAGE_DIR"
fi

# 古いバックアップを削除
find "$BACKUP_DIR" -maxdepth 1 -mindepth 1 -type d -mtime "+$KEEP_DAYS" -exec rm -rf {} +
echo "  古いバックアップ削除完了（${KEEP_DAYS}日超）"

echo "[$TIMESTAMP] バックアップ完了: $DEST"
