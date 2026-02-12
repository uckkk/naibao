#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-"${ROOT_DIR}/deploy/.env.prod"}"
COMPOSE_FILE="${COMPOSE_FILE:-"${ROOT_DIR}/deploy/docker-compose.prod.yml"}"

if [ ! -f "${ENV_FILE}" ]; then
  echo "错误: 找不到 ${ENV_FILE}"
  echo "请先执行：cp deploy/.env.prod.example deploy/.env.prod 并填入真实值"
  exit 1
fi

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps

