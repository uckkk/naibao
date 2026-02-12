#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-"${ROOT_DIR}/deploy/.env.prod"}"
COMPOSE_FILE="${COMPOSE_FILE:-"${ROOT_DIR}/deploy/docker-compose.prod.yml"}"

if [ ! -f "${ENV_FILE}" ]; then
  echo "错误: 找不到 ${ENV_FILE}"
  exit 1
fi

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" down

