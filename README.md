# 奶宝 - 纯奶粉喂养APP

## 项目简介

专注纯奶粉喂养的垂直赛道工具，为0-12个月宝宝父母提供科学的喂养记录和数据追踪。

## 技术栈

### 前端
- **框架**: uni-app 3.x (Vue 3 + TypeScript)
- **架构**: vue + nvue混合（核心页面使用nvue原生渲染）
- **状态管理**: Pinia
- **支持平台**: iOS、Android、鸿蒙、微信小程序

### 后端
- **语言**: Go 1.21+
- **框架**: Gin
- **WebSocket**: gorilla/websocket（实时同步）
- **ORM**: GORM

### 数据库
- **主数据库**: PostgreSQL 15+ (腾讯云 TDSQL-C)
- **缓存**: Redis 7+

## 项目结构

```
naibao/
├── frontend/          # uni-app前端项目
├── backend/           # Go后端项目
├── database/          # 数据库SQL文件
│   ├── schema.sql     # 表结构
│   └── init_data.sql  # 初始化数据
└── docs/             # 设计文档
```

## 快速开始

### 后端启动

```bash
cd backend
go mod download
go run main.go
```

### 前端启动

```bash
cd frontend
npm install
npm run dev:h5        # H5开发
npm run dev:mp-weixin # 微信小程序开发
npm run dev:app       # App开发
```

## 环境变量

### 后端（backend/.env）

复制示例配置：

```bash
cp backend/.env.example backend/.env
```

`backend/.env` 示例内容：

```env
# 服务器配置
SERVER_PORT=8080
GIN_MODE=debug

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=naibao
DB_SSLMODE=disable

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# JWT配置
JWT_SECRET=your-secret-key
```

### 前端（frontend/.env.local）

用于配置 API 地址（本机私有，不提交）：

```bash
cp frontend/.env.example frontend/.env.local
```

例如：

```env
VITE_API_BASE_URL=http://localhost:8080
```

## 数据库初始化

```bash
psql -U postgres -d naibao -f database/schema.sql
psql -U postgres -d naibao -f database/init_data.sql
```

## 核心功能

- ✅ 一键投喂（智能推荐奶量）
- ✅ 喂养记录和时间轴
- ✅ 数据统计和分析
- ✅ 多设备多角色同步
- ✅ 奶粉规格和勺数提示
- ✅ 卫健委标准数据支持
- ✅ 邀请码分享家人

## 文档

文档入口：`docs/README.md`

建议先读：
- 现状画像与问题清单：`docs/PROJECT_AUDIT.md`
- 最优解方案：`docs/OPTIMAL_SOLUTION.md`
- 可执行重构计划：`docs/REFACTOR_PLAN.md`

## License

MIT
