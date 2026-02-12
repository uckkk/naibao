# Cloudflare Tunnel 托管后端（api.naibao.me）

目标：后端与数据库跑在你的本机（Docker），通过 Cloudflare Tunnel 暴露成固定域名：

- `https://api.naibao.me`

并让前端（GitHub Pages 的 `https://naibao.me`）跨域访问后端 API。

## 0) 前置条件

- 你已把 `naibao.me` 添加到 Cloudflare，并把域名 NS 切换到 Cloudflare（DNS 托管在 Cloudflare）
- 本机可运行 docker

## 1) 本机启动后端（Docker）

首次运行运营台会自动生成：

- `deploy/.env.home`

你也可以手动准备：

```bash
cp deploy/.env.home.example deploy/.env.home
```

然后打开运营台（推荐）：

```bash
./scripts/local_ops.sh
```

在网页里点 **“启动/修复全部”**，确保：

- `http://127.0.0.1:8080/health` 返回 ok

## 2) 创建 Named Tunnel（只需做一次）

> 注意：这一步需要你登录 Cloudflare 授权（cloudflared 会打开浏览器）。

### 方式 A（推荐）：macOS 双击一键初始化

- 双击运行仓库根目录：`奶宝固定外网域名初始化.command`

它会做：
- `cloudflared tunnel login`
- 创建/复用 tunnel（默认名 `naibao-api`）
- 尝试创建 `api.naibao.me` DNS 路由（若域名还未切到 Cloudflare NS，会提示并可在切换后重跑）
- 生成本项目配置：`.naibao_runtime/cloudflared_named.yml`（不覆盖 `~/.cloudflared/config.yml`）

完成后回到运营台，点“启动 Tunnel”即可。

### 方式 B：手动命令行（可选）

```bash
cloudflared tunnel login
cloudflared tunnel create naibao-api
cloudflared tunnel route dns naibao-api api.naibao.me
```

然后创建配置文件（macOS/Linux 默认位置）：

- `~/.cloudflared/config.yml`

内容示例（把 UUID 与 credentials-file 改成你真实路径；仓库里也有模板 `deploy/cloudflared/config.example.yml`）：

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: ~/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: api.naibao.me
    service: http://127.0.0.1:8080
  - service: http_status:404
```

## 3) 启动 Tunnel

方式 A：用运营台按钮（推荐）  
方式 B：命令行：

```bash
cloudflared tunnel run naibao-api
```

## 4) 验证

```bash
curl -fsSL "https://api.naibao.me/api/health"
```

预期：

```json
{"status":"ok"}
```

## 5) CORS（让 naibao.me 能访问 api.naibao.me）

确保 `deploy/.env.home` 里有：

```env
CORS_ALLOW_ORIGINS=https://naibao.me,https://www.naibao.me
```

改完后在运营台里重启后端（或 `docker compose restart backend`）。
