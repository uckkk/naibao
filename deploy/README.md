# 线上最低成本部署（同源 /api，适合中国用户）

目标：
- 前端：纯静态站点（H5），尽量把展示/交互/计算留在客户端
- 后端：只处理用户数据（API + WebSocket），同源 `/api` 与 `/ws` 反代，避免跨域与端差异
- 成本与维护：一台服务器 + Docker Compose + 自动 HTTPS（Caddy）

## 0) 你需要准备什么

- 一台服务器（推荐：腾讯云轻量应用服务器 / 阿里云轻量）
  - **优先中国大陆机房**：访问更稳，但通常需要域名备案
  - 不想备案：可先用 **香港/新加坡**，体验略差但可快速上线
- 一个域名（用于 HTTPS，系统通知/隐私能力在非 HTTPS 下会受限）
- 安全组/防火墙放行端口：`80`、`443`

## 1) 服务器上一次性准备（Docker）

以 Ubuntu/Debian 为例：

```bash
apt update -y
apt install -y docker.io docker-compose-plugin git
systemctl enable --now docker
```

## 2) 拉代码与配置环境变量

建议放到 `/opt/naibao`：

```bash
mkdir -p /opt/naibao
cd /opt/naibao
git clone https://github.com/uckkk/naibao.git .
```

复制生产配置并修改：

```bash
cp deploy/.env.prod.example deploy/.env.prod
nano deploy/.env.prod
```

至少需要填写：
- `DOMAIN`（你的域名，例如 `naibao.example.com`）
- `POSTGRES_PASSWORD`
- `JWT_SECRET`（建议 32+ 位随机字符串）

建议同时覆盖 `www`（可选）：
- `DOMAIN=naibao.me, www.naibao.me`

## 3) 一键启动（构建前端 + 反代 + 后端 + 数据库）

在仓库根目录执行：

```bash
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d --build
```

## 4) 验证

```bash
curl -fsSL "https://$DOMAIN/api/health"
```

预期：

```json
{"status":"ok"}
```

浏览器打开：
- `https://$DOMAIN`（H5 站点）

## 5) 更新发布（以后每次）

```bash
cd /opt/naibao
git pull
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d --build
```

## 6) 常见坑（中国用户）

- **没有 HTTPS**：系统通知/权限等能力会受限（尤其 iOS）
- **大陆机房 + 域名未备案**：可能无法访问或被拦截（建议先用香港机房快速上线，备案完成后再迁移）
