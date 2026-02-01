#!/bin/bash

# scripts/* 通用配置加载与小工具函数
# - 支持从 scripts/.env.local 读取本机私有配置（该文件应被 git 忽略）
# - 统一 SSH/部署相关变量，降低脚本维护成本

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_LOCAL="${SCRIPTS_DIR}/.env.local"

if [ -f "${ENV_LOCAL}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${ENV_LOCAL}"
  set +a
fi

# Defaults (can be overridden by env / .env.local)
SSH_HOST="${SSH_HOST:-}"
SSH_USER="${SSH_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
SSH_KEY="${SSH_KEY:-}"
SSH_PASSWORD="${SSH_PASSWORD:-}"

REMOTE_BASE="${REMOTE_BASE:-/opt/naibao}"

require_var() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "❌ 缺少环境变量: ${name}" >&2
    echo "   你可以复制 scripts/.env.example 为 scripts/.env.local 并填写真实值（该文件不会被提交）。" >&2
    return 1
  fi
}

