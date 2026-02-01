# 代码与结构重构计划（可执行清单）

## P0（必须做，修复“跑不通/体验差”）

### 后端（Go）

- [x] 修复编译问题
  - [x] `backend/handlers/auth.go`：移除未定义字段引用（以“手机号+密码”为主）。
  - [x] `backend/router/router.go`：修正统计路由到真实实现方法。
  - [x] `backend/handlers/growth.go`：修复指针字段赋值类型。
- [x] 补齐前端依赖的接口
  - [x] `PUT /api/user/avatar`
  - [x] `GET /api/babies/:id/daily-records`
- [x] 修复统计正确性（限定当天范围）
- [x] 家庭协作基础一致性：创建宝宝写入默认 `family_members`（owner/admin）

### 前端（uni-app）

- [x] `frontend/src/utils/api.js`：GET 请求拼接 query string（H5 fetch 场景不再丢参数）
- [x] 首页数据加载：减少重复请求（降低一次网络往返）

## P1（强烈建议，降低长期维护成本）

- [x] 配置与环境
  - [x] 前端改为 `VITE_API_BASE_URL`（`frontend/.env.local`）配置，避免写死 IP
  - [x] 后端 `config.Load()` 一次性加载（缓存）
  - [x] 数据库迁移策略：`DB_AUTO_MIGRATE` 可控（生产建议关闭）
- [x] 文档归档：根目录文档迁入 `docs/` 并建立索引

## P2（可选增强）

- [ ] 删除仓库冗余（按需）
  - [ ] `frontend/node_modules/` 保持不入库（本机可随时 `npm ci` 重建）
  - [ ] 进一步清理未使用文件（以实际引用为准）
- [x] 统一静态资源目录：收敛到 `frontend/src/static/`，并补齐缺省资源

## 验证（每次改动都要能跑通）

- 前端：`cd frontend && npm run build:h5`
- 后端：本机需安装 Go 后执行 `cd backend && go test ./...`（至少保证可编译）
