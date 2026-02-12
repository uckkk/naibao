#!/usr/bin/env bash

# 生产环境最小初始化（推荐搭配 deploy/docker-compose.prod.yml）
#
# 目标：
# - 只安装运行所需的基础依赖：docker / compose / git
# - 业务依赖（Postgres/Caddy/后端）全部用容器管理，降低运维复杂度
#
# 适用：Ubuntu / Debian

set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "错误: 请用 root 运行（或 sudo）"
  exit 1
fi

echo "[prod_init] apt update..."
apt update -y

echo "[prod_init] install docker + compose plugin + git..."
apt install -y docker.io docker-compose-plugin git curl ca-certificates

echo "[prod_init] enable docker..."
systemctl enable --now docker

mkdir -p /opt/naibao

echo ""
echo "[prod_init] done."
echo "下一步："
echo "1) cd /opt/naibao && git clone https://github.com/uckkk/naibao.git ."
echo "2) cp deploy/.env.prod.example deploy/.env.prod && 编辑 DOMAIN/POSTGRES_PASSWORD/JWT_SECRET"
echo "3) docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d --build"

