# 🚀 快速部署指南

## 服务器信息

请将真实服务器信息写入项目根目录的 `服务器配置信息.md`（已忽略不提交），或先用模板：

- [服务器配置信息模板](服务器配置信息模板.md)

---

## ⚡ 快速开始

> 说明：下面命令默认在“项目根目录”执行（能直接使用 `./scripts/*`）。

### 推荐：Docker 生产一体化部署（最低成本、最好维护）

适合“线上只处理用户数据，其他都在客户端运行”的目标：前端静态 + 同源 `/api` + 自动 HTTPS。

- 入口文档：`deploy/README.md`

一条命令启动（在服务器上）：

```bash
./scripts/prod_up.sh
```

### 1. 测试连接

```bash
./scripts/test_connection.sh
```

### 2. 初始化服务器（首次部署）

```bash
# 先配置环境变量（或从 服务器配置信息.md 复制）
export SERVER_IP="your.server.ip"
export SERVER_USER="root"

# 连接服务器
ssh ${SERVER_USER}@${SERVER_IP}

# 运行初始化脚本
bash /opt/naibao/scripts/server_init.sh
```

### 3. 部署代码

```bash
# 使用部署脚本（推荐）
./scripts/deploy.sh

# 或手动部署
scp -r backend ${SERVER_USER}@${SERVER_IP}:/opt/naibao/
scp -r database ${SERVER_USER}@${SERVER_IP}:/opt/naibao/
```

### 4. 配置和启动

```bash
# 连接服务器
ssh ${SERVER_USER}@${SERVER_IP}

# 配置环境变量
cd /opt/naibao/backend
nano .env  # 编辑配置文件

# 初始化数据库
psql -U naibao_user -d naibao -f /opt/naibao/database/schema.sql
psql -U naibao_user -d naibao -f /opt/naibao/database/init_data.sql

# 编译和运行
go mod download
go build -o naibao-server main.go
./naibao-server
```

---

## 📚 详细文档

- [部署指南.md](部署指南.md) - 详细的部署步骤

---

## ⚠️ 安全提醒

1. **不要明文写入仓库**：账号/密码/密钥等请放在 `服务器配置信息.md`（已忽略）或密码管理器
2. **不要提交**：`.gitignore` 已配置（如 `*.env`、`服务器配置信息.md`），避免敏感文件入库
3. **定期备份**：建议设置数据库自动备份
4. **更新系统**：定期更新服务器系统和软件包

---

**开始部署吧！** 🎉
