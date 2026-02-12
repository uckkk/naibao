#!/usr/bin/env bash

# PostgreSQL 备份（docker compose 生产形态）
#
# - 默认仅生成备份文件，不做删除
# - 如需按“保留 7 天”自动清理：加参数 --prune
#
# 依赖：
# - docker + docker compose plugin
# - 使用 deploy/docker-compose.prod.yml

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-"${ROOT_DIR}/deploy/.env.prod"}"
COMPOSE_FILE="${COMPOSE_FILE:-"${ROOT_DIR}/deploy/docker-compose.prod.yml"}"

if [ -f "${ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  set -a
  . "${ENV_FILE}"
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-naibao}"
POSTGRES_USER="${POSTGRES_USER:-naibao_user}"

BACKUP_DIR="${BACKUP_DIR:-"${ROOT_DIR}/backups/postgres"}"
mkdir -p "${BACKUP_DIR}"

TS="$(TZ=Asia/Shanghai date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/naibao_${TS}.sql.gz"

echo "[pg_backup] start -> ${OUT_FILE}"

# 在 db 容器内通过本地 socket 执行 pg_dump（官方镜像默认 local trust，不需要暴露密码）
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-privileges \
  | gzip -9 > "${OUT_FILE}"

echo "[pg_backup] done"

if [ "${1:-}" = "--prune" ]; then
  # 只清理备份目录下的旧备份文件（保留最近 7 天）
  echo "[pg_backup] prune backups older than 7 days in ${BACKUP_DIR}"
  find "${BACKUP_DIR}" -type f -name "*.sql.gz" -mtime +7 -print -delete || true
fi

