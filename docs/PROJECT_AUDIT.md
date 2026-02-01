# 项目现状画像（naibao）

> 目标：给出当前仓库“可运行程度/维护成本/上线风险”的客观画像，并标注已落地的修复与仍需关注的风险。
>
> 说明：本文聚焦“现状问题清单（带定位/优先级）”，最优解路线见 `docs/OPTIMAL_SOLUTION.md`，可执行计划见 `docs/REFACTOR_PLAN.md`。

## 1. 产品定位（从仓库内容推断）

- 产品：`奶宝`，面向 0-12 个月纯奶粉喂养家庭的记录/提醒/数据分析工具。
- 核心心智：一键投喂、时间轴与倒计时、按卫健委标准的可解释参考、（可扩展）家庭协作共享同一宝宝。

## 2. 技术栈与结构

### 2.1 目录结构（当前）

- `frontend/`：uni-app（Vue 3 + Pinia + Vite），混合 `vue`/`nvue` 页面。
- `backend/`：Go + Gin + GORM + JWT（Redis 可选）。
- `database/`：PostgreSQL `schema.sql` + `init_data.sql`（结构与初始化数据作为唯一来源）。
- `scripts/`：服务器初始化/部署/验证脚本（已统一改为读取 `scripts/.env.local`，避免写死 IP/密码）。
- `docs/`：文档已分层归档（产品/技术/运维/测试/报告），入口见 `docs/README.md`。

### 2.2 运行方式（当前）

- 后端：`cd backend && go run main.go`（需要本机安装 Go）。
- 前端：`cd frontend && npm run dev:h5` / `npm run dev:mp-weixin` / `npm run dev:app`。

## 3. 已落地修复（影响 UX/稳定性/维护成本的 P0/P1）

- 后端编译级问题与路由契约缺口已修复（注册/登录、喂养统计、每日记录、用户头像等核心链路）。
- 前端 API 客户端已修复 H5 fetch 场景下 GET query 参数丢失问题（避免 `baby_id` 丢失导致数据为空）。
- 配置去硬编码：前端通过 `VITE_API_BASE_URL`（`frontend/.env.local`）配置 API；脚本通过 `scripts/.env.local` 配置 SSH。
- 静态资源已收敛到 `frontend/src/static/`，并补齐 `default-avatar`、`tabbar`、`avatars`、`bottle-*` 等缺省资源，避免运行时 404。
- 文档体系已迁入 `docs/` 并建立索引，降低检索与维护成本。

## 4. 当前主要缺陷清单（按“体验/维护成本/上线风险”排序）

> 优先级约定：P0=阻塞验收/明显错误；P1=影响体验与长期维护；P2=可优化但不阻塞。

### 4.1 P0（必须先修）

1) **（已修复）H5 自研路由 + `uni` polyfill 增加跨端风险**
   - 现象：历史上曾通过 `frontend/src/utils/router.js` + `frontend/src/utils/uni-polyfill.js` 自行模拟 `uni` 运行时。
   - 处理：已切回官方 `uni` CLI + `uni-h5` 运行时；相关自研文件已删除（`frontend/src/utils/router.js`、`frontend/src/utils/uni-polyfill.js`、`frontend/src/utils/picker-polyfill.js`），页面不再依赖 DOM polyfill。
   - 结果：显著降低跨端差异与维护成本（H5/小程序/App 共享同一运行时与生命周期）。
   - 相关文件：`frontend/vite.config.js`、`frontend/src/main.js`

2) **数据页“建议文案”显示错误（可视为功能缺陷）**
   - 现象：`frontend/src/pages/data-detail/index.vue` 的 `.reference-suggestion` 文字颜色为 `#fff`，但所在背景为白色，导致文字不可见。
   - 相关文件：`frontend/src/pages/data-detail/index.vue`

3) **“下次喂奶时间/倒计时”前后端字段未统一，存在 Safari 时间解析差异风险**
   - 现象：后端 `GET /api/feedings/stats` 已返回 `next_feeding_timestamp`（秒），但首页倒计时仍优先解析 `stats.next_feeding_time` 字符串。
   - 风险：iOS Safari 对日期字符串解析差异会导致倒计时异常；同一业务字段分散在不同结构里也增加维护成本。
   - 相关文件：`backend/handlers/feeding.go`、`frontend/src/pages/home/index.vue`

### 4.2 P1（强烈建议修）

1) **（已修复）同一路径存在 `.vue` 与 `.nvue` 双实现，逻辑/样式长期必然漂移**
   - 现象：历史上 `frontend/src/pages/home/index.vue` 与 `frontend/src/pages/home/index.nvue` 并存。
   - 处理：已删除 `frontend/src/pages/home/index.nvue`，首页以 `frontend/src/pages/home/index.vue` 为唯一实现。
   - 结果：避免双实现漂移，减少端差异与维护成本。

2) **设计语言不统一（颜色/字号/密度/组件形态），导致产品“像拼装”**
   - 现象：登录/注册页面使用偏紫渐变；首页以金色为主；数据页又出现紫色强调与不可见文案；品牌色表分散在页面内部。
   - 风险：体验不高级、难形成记忆点；未来改视觉要改多处。
   - 相关文件：`frontend/src/pages/login/index.vue`、`frontend/src/pages/register/index.vue`、`frontend/src/pages/data-detail/index.vue`、`frontend/src/pages/formula-select/index.vue`、`frontend/src/App.vue`

3) **缺少统一的“加载态/空态/错误态”规范**
   - 现象：页面多为“直接请求 + console.error”，用户只看到空白或默认值；错误信息散落在各页。
   - 风险：弱网/后端异常时体验差；排障成本高。
   - 相关文件：`frontend/src/pages/*/*.vue`、`frontend/src/utils/api.js`

4) **后端“家庭协作”在权限模型上尚未闭环**
   - 现象：部分接口以 `babies.user_id = 当前用户` 校验；但又提供 `family_members` 查询。
   - 风险：若按产品承诺支持多人协作，权限/数据一致性会成为线上 P0；否则应当显式降级为“单用户单宝宝”以降低维护。
   - 相关文件：`backend/handlers/baby.go`、`backend/handlers/feeding.go`、`backend/handlers/growth.go`、`backend/handlers/family.go`

5) **安全与可控性：`AdminOnly` 中间件为空实现**
   - 风险：一旦未来补充 admin 路由但忘记实现鉴权，会产生安全事故。
   - 相关文件：`backend/router/middleware/admin.go`

### 4.3 P2（可优化/减债）

1) **测试与脚本可继续标准化**
   - 已有：`scripts/smoke_test.py`、`scripts/e2e_h5_check.spec.js`
   - 可选：补充最小 CI（只做 build + smoke + e2e），避免回归。

2) **仓库内存在多份相似的手机测试/数据库文档**
   - 风险：文档漂移、信息不一致；应收敛到 1 份权威入口。
   - 相关目录：`docs/test/`

3) **冗余/一次性测试页面可清理（但属于删除操作，建议最后统一处理）**
   - 相关文件：`frontend/quick-test.html`、`frontend/test-api.html`、`frontend/test-connection.html` 等

## 5. 仍需关注的风险与改进点（上线视角）

- **安全**：请确保真实服务器密码/密钥仅存在于本机忽略文件（如 `服务器配置信息.md` / `*.env.local`），并考虑轮换历史泄露过的凭据。
- **发布与合规**：小程序/生产环境通常要求 HTTPS + 域名白名单；如涉及健康建议与数据收集，需关注隐私合规与审核口径。
- **可观测性**：建议补齐最小化日志/监控/备份策略（尤其是 PostgreSQL 备份与恢复演练）。
- **测试**：当前缺少自动化测试与 CI 校验（至少应做到“能编译+基础接口冒烟测试”）。
