# scripts 使用说明

> 这些脚本主要面向“单机部署”（轻量服务器：后端 + PostgreSQL + Redis）。

## 统一配置（推荐）

为避免在仓库内写死服务器 IP/密码，`scripts/*` 脚本统一从环境变量读取，并支持本机私有配置文件：

```bash
cp scripts/.env.example scripts/.env.local
$EDITOR scripts/.env.local
```

至少需要配置：

- `SSH_HOST`
- `SSH_USER`（默认 root）
- `SSH_PORT`（默认 22）

## 脚本列表

- `scripts/init_ssh.sh`：初始化本机 SSH 连接环境（生成/配置密钥等）。
- `scripts/add_ssh_key.exp`：辅助写入 SSH 密钥（expect）。
- `scripts/test_connection.sh`：测试 SSH 连接/端口/基础连通性。
- `scripts/server_init.sh`：服务器初始化（apt 更新、安装 PostgreSQL/Redis/Go、配置防火墙等；需 root）。
- `scripts/deploy.sh`：上传 `backend/` + `database/` 到服务器并执行基础步骤（读取 `scripts/.env.local` / 环境变量）。
- `scripts/setup_db.sh`：数据库初始化/导入 schema 与 init data。
- `scripts/verify_database.sh`：验证数据库可用性与表结构。
- `scripts/update_backend.sh`：更新后端代码并重启（具体行为依赖脚本内容）。
- `scripts/start_server.sh`：在服务器上启动后端二进制（使用 `server.pid` + `server.log`）。
- `scripts/stop_server.sh`：停止后端服务（读 `server.pid`）。
- `scripts/dev_local.sh`：本地一键启动（Docker）+ API 冒烟测试 + 前端构建（用于验收前自检）。
- `scripts/smoke_test.py`：API 功能冒烟测试（无第三方依赖）。

## 建议执行顺序（新服务器）

1) 本机：`scripts/init_ssh.sh` → `scripts/test_connection.sh`
2) 服务器：`scripts/server_init.sh`
3) 本机：`scripts/deploy.sh`
4) 服务器/本机：`scripts/setup_db.sh` → `scripts/verify_database.sh`
5) 服务器：`scripts/start_server.sh`

## 注意事项

- `scripts/server_init.sh` 会修改系统包/防火墙/数据库配置，属于高影响操作，务必在新机器或确认的环境执行。
- 如需脚本自动化密码输入，可设置 `SSH_PASSWORD` 并安装 `sshpass`（不推荐；建议改用密钥认证）。
