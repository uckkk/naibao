# 静态资源与构建产物规范（减少重复与维护成本）

## 目标

- 多端一致：同一套资源路径策略在 H5 / 小程序 / App 上都可用。
- 单一真相来源：同一份图片/字体/图标只保留一处，避免“改一处漏一处”。
- 构建产物不入库：保证仓库干净、可复现。

## 现状（仓库内）

- 资源来源已收敛到：`frontend/src/static/`（uni-app 多端通用）
- 构建产物目录（不入库/不提交）：
  - `frontend/dist/`（H5 build 产物，已在 `.gitignore` 忽略）

## 推荐策略（面向 uni-app 多端）

### 1) 资源目录：统一到 `frontend/src/static/`（推荐）

- 建议长期维护：`frontend/src/static/`
- 页面中优先使用：`/static/...` 绝对路径（uni-app 多端通用的习惯用法）
- 禁止同一资源同时存在于 `public/static` 与 `src/static`（避免双源）

优点：
- 与 uni-app 官方约定一致，多端最稳
- 排障成本低（路径规则统一）

### 2) H5 仅方案：统一走 Vite import（不推荐作为多端最终形态）

- 所有图片通过 `import xxxUrl from '...?.url'` 或 `new URL(..., import.meta.url)` 引入
- 不再依赖 `public/static`

优点：
- 纯 H5 体验更“现代”

缺点：
- 小程序/原生端资源处理规则不同，维护成本更高

## 待清理清单（供你确认后再做）

1) 确认是否需要保留 `frontend/public/`（目前为空，可删除或留作 Vite 约定目录）
2) 如需更美观的默认头像/Tab 图标：用设计稿替换 `frontend/src/static/*` 下的占位 PNG
