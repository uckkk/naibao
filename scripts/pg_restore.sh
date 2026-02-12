#!/usr/bin/env bash

# PostgreSQL 恢复演练（安全默认：恢复到新库，不覆盖线上库）
#
# 用法：
#   ./scripts/pg_restore.sh /path/to/naibao_YYYYMMDD_HHMMSS.sql.gz [target_db]
#
# 说明：
# - 默认 target_db=naibao_restore
# - 若 target_db 已存在会失败（避免误覆盖）

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-"${ROOT_DIR}/deploy/.env.prod"}"
COMPOSE_FILE="${COMPOSE_FILE:-"${ROOT_DIR}/deploy/docker-compose.prod.yml"}"

BACKUP_FILE="${1:-}"
TARGET_DB="${2:-naibao_restore}"

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
  echo "用法: $0 /path/to/backup.sql.gz [target_db]"
  exit 1
fi

if ! [[ "${TARGET_DB}" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "错误: target_db 仅允许字母/数字/下划线"
  exit 1
fi

if [ -f "${ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  set -a
  . "${ENV_FILE}"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-naibao_user}"

echo "[pg_restore] create database: ${TARGET_DB}"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  psql -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE ${TARGET_DB};"

echo "[pg_restore] restore -> ${TARGET_DB} from ${BACKUP_FILE}"
gzip -dc "${BACKUP_FILE}" | docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  psql -U "${POSTGRES_USER}" -d "${TARGET_DB}" -v ON_ERROR_STOP=1

echo "[pg_restore] done: restored to ${TARGET_DB}"
echo "[pg_restore] 下一步：把后端 DB_NAME 临时指向该库做验证，然后再决定是否切换/覆盖。"

