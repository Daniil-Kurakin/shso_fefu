#!/usr/bin/env bash
set -euo pipefail

# =====================================================================
# Резервное копирование PostgreSQL и Media для ШСО ДВФУ
# Использование: bash scripts/backup.sh
# Рекомендуется добавить в crontab: 0 3 * * * /path/to/scripts/backup.sh
# =====================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR"

echo "==> Создание дампа PostgreSQL..."
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U shso shso | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

echo "==> Создание архива медиа-файлов..."
docker compose -f docker-compose.prod.yml exec -T web tar -czf - -C /app media > "$BACKUP_DIR/media_$TIMESTAMP.tar.gz" 2>/dev/null || true

echo "==> Очистка старых бэкапов (старше $RETENTION_DAYS дней)..."
find "$BACKUP_DIR" -type f -name "*.gz" -mtime +$RETENTION_DAYS -delete

echo "==> Бэкап успешно сохранен в $BACKUP_DIR ($TIMESTAMP)"
