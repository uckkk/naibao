# 奶宝（Naibao）PRD（反推版）

版本: v1.0  
更新时间: 2026-02-05  
目标读者: 产品 / 设计 / 前端 / 后端 / 测试 / AI 编程工具  
文档目的: 仅凭本文即可从零重写一个与当前项目等价（或更一致）的「纯奶粉喂养」移动端产品（以中国用户与 iOS 体验为基线）。

---

## 0. 一句话定义

面向 0-12 个月纯奶粉喂养家庭的「一键记录 + 倒计时 + 今日节奏 + 家庭协作」工具: 少打扰、低焦虑、好交接。

---

## 1. 背景与目标

### 1.1 目标人群

- 中国宝爸宝妈（尤其是夜间、睡眠不足场景）
- 需要多人交接（夫妻/老人/保姆）共同记录同一宝宝喂养数据
- 以「纯奶粉喂养」为主（本产品不覆盖母乳、辅食等复杂场景）

### 1.2 核心目标（产品层）

- 30 秒内完成首次上手并记录第一条喂奶（尽量少填信息）
- 首页只呈现用户当下最关心的 3 件事:
  1) 现在离“下一次建议喂奶”还剩多久 / 已超时多久  
  2) 今日奶量进度（对目标的直观感知）  
  3) 今天的喂奶节奏（24h 时间轴 + 事件点）
- 降低误操作成本:
  - 关键操作可撤销（记录后 3 秒内撤销）
  - 明显异常（过密、单次过大、今日超参考明显）用“轻、可执行”的 iOS 风格提示引导核对，而不是制造恐慌
- 多设备 / 多成员实时同步（不要求“强实时”，但要做到“几百毫秒后自动刷新”）

### 1.3 非目标（当前不做/不承诺）

- 医疗诊断与医嘱（仅趋势参考 + 免责声明）
- 母乳 / 辅食 / 睡眠等多维复杂记录
- 系统级推送通知（当前仅“应用内提醒”，需保持应用打开）
- 蓝牙奶瓶/手环等硬件接入

---

## 2. 设计原则（iOS + 本地化）

### 2.1 iOS 体验原则

- 信息克制: 默认只展示关键数字与图形化状态；解释性内容放入底部 Sheet，按需展开
- 交互收敛: 全站统一弱网/错误/空态/确认/说明的样式与交互，不让用户在不同页面“重新学习”
- 可撤销优先于“二次确认”: 记录这种高频动作默认直接执行，然后给撤销窗口；对高风险输入（例如单次 > 200ml、分钟级过密记录）再使用确认 Sheet
- 轻量可执行提示: 提示要能落到下一步（例如“去核对今日记录”/“撤销多余记录”/“去调整喂奶间隔”）

### 2.2 本地化原则（中国父母）

- 文案避免“评判/打分”，用“状态稳 / 需留意 / 建议处理”等可执行状态词
- 时间展示使用 24 小时制（00:00-24:00 语义）
- 弱网场景明确提示“数据可能无法同步”，提供重试

---

## 3. 信息架构（IA）

### 3.1 顶层导航

产品不依赖底部 TabBar（可保留“占位 tabBar”仅用于框架兼容，但视觉上不出现）。主要入口:

- 首页（核心）
- 设置（收拢所有入口）
- 首页 -> 今日抽屉（今日记录、时间轴、编辑/删除）
- 首页 -> 数据详情（趋势与参考范围）

### 3.2 页面清单

- 登录: `/pages/login/index`
- 注册: `/pages/register/index`
- 首页: `/pages/home/index`
- 设置: `/pages/settings/index`
- 宝宝资料: `/pages/baby-info/index`
- 选择头像: `/pages/avatar-select/index`（支持 user/baby）
- 喂奶设置: `/pages/feeding-settings/index`
- 投喂偏好: `/pages/preference/index`
- 选择奶粉: `/pages/formula-select/index`
- 冲泡要求: `/pages/formula-spec/index`
- 数据详情: `/pages/data-detail/index`
- 数据报告: `/pages/report/index`
- 家庭共享: `/pages/family/index`
- 帮助/常见问题: `/pages/help/index`
- 管理后台: `/pages/admin/index`（仅管理员）

---

## 4. 全局交互规范（必须全站一致）

### 4.1 弱网/离线提示（Network Banner）

- 触发: 设备离线或网络不可用
- 表现: 顶部固定/吸顶提示条，文案固定: `网络不可用：数据可能无法同步`，提供 `重试`
- 行为:
  - 点击重试: 刷新网络状态，若恢复则 toast `网络已恢复`，并触发页面 `retry` 回调

### 4.2 Loading / Error / Empty（State）

全站使用统一状态组件（视觉一致，避免“页面集合感”）:

- `loading`: 加载中（可不展示骨架，保持克制）
- `error`: 加载失败 + 错误描述 + `重试` 按钮
- `empty`: 空态文案要给出下一步（如“去建档”“点投喂开始”）
- 允许 `embedded`（嵌入卡片/分组内时弱化边框与阴影）

### 4.3 说明 / 确认（Sheet）

禁止使用系统风格突兀的弹窗堆砌解释文案；统一使用底部 Sheet:

- 说明 Sheet:
  - 标题 + 简短 desc（告诉用户“为什么要看它”）
  - 内容尽量图形化（RangeBar/gauge），少段落
  - 主/次按钮可选
- 确认 Sheet（NbConfirmSheet）:
  - 用于高风险操作（删除、超大奶量确认、分钟级过密记录提醒）
  - 支持 `danger` 主按钮样式

### 4.4 iOS 左滑列表

- 今日记录列表支持左滑露出操作:
  - 编辑
  - 删除（danger）
- 交互优先级: 滑动 > 点击，避免误触

### 4.5 误触可撤销（Undo Toast）

记录喂奶后:

- 3 秒内底部出现撤销条（不可遮挡主按钮）
- 主动作: `撤销`
- 次动作: 根据异常类型显示 `查看/说明/核对`
- 目的: 降低“连续点两次 / 半夜误触”的焦虑成本

---

## 5. 核心页面需求

### 5.1 登录 / 注册

目标: 降摩擦进入首页；token 过期自动回到登录。

- 登录输入:
  - 手机号（11 位，正则校验）
  - 密码
- 注册输入:
  - 手机号
  - 昵称（可选）
  - 密码（>= 6）
  - 确认密码
- 成功后:
  - 存储 token
  - `reLaunch` 到首页

### 5.2 宝宝建档（宝宝资料）

目标: 最少信息即可开用；其他可后补。

- 必填:
  - 昵称
  - 出生日期
- 兼容字段（可选，提升推荐准确度）:
  - 出生时间（若未填，创建时默认 `12:00`）
  - 体重（kg）
  - 身高（cm）
  - 性别
  - 头像
- 权限:
  - 仅家庭管理员可编辑宝宝基础信息（避免成员误改）
- 保存后:
  - 创建宝宝时自动成为该宝宝家庭管理员（family_members role=admin）
  - 可选: 同步把体重/身高写入当天 growth_records（upsert）

### 5.3 首页（唯一主入口）

#### 5.3.1 首页信息结构（必须克制）

首页不使用“多卡片堆叠”，信息居中、聚焦。

1) 顶部宝宝信息条（Baby Chip）
   - 显示: 头像、昵称、月龄/天数、星座（可选）
   - 点击整条进入「数据详情」
   - 点击头像进入「宝宝资料」
   - 右侧固定入口:
     - `今日`（打开今日抽屉）
     - `设置`

2) 新手轻提示（Setup Nudge）
   - 只是一行引导 + 进度，不做大面板
   - 可关闭（本地记忆）
   - 引导项（建议顺序）:
     - 宝宝资料（已完成/未完成）
     - 绑定奶粉（可跳过）
     - 喂奶间隔与提醒

3) 核心 Hero 区（“喂奶节奏”）
   - 标题: `喂奶节奏`
   - 状态徽标（pill）:
     - `待记录 / 状态稳 / 需留意 / 建议处理`
     - 点击打开「状态说明 Sheet」
   - 主信息（倒计时/超时）:
     - Tag: `还剩` 或 `超时`
     - 主文案: `HH小时MM分`（或更短格式），无记录时显示 `点“投喂”开始`
   - 节奏轨道（一个轨道表达 3 件事）:
     - 24 小时轴（0-24）
     - 上次喂奶 -> 下一次建议喂奶 的“建议窗口”（window）
     - 从上次到现在的“进度填充”（fill）
     - 今天的喂奶事件点（仅点，不堆文案；聚类避免重叠）
     - 不额外叠加“当前时间竖线”（减少干扰）
   - 二级文案: `距上次 xx`（若未设置间隔则引导去设置）

4) 主动作区（Feed Zone）
   - 近距离贴近 Hero，避免用户视线/手指距离过大
   - 按钮:
     - 文案: `投喂`
     - 副文案: 默认显示建议奶量 `xxx ml`
   - 图形化进度:
     - 环形进度表达 `今日已喝 / 今日目标`（目标缺失时弱化）
   - 记录成功提示:
     - toast `记录成功`
     - 出现 Undo Toast（3 秒）

#### 5.3.2 首页关键交互规则

- 一键记录:
  - 默认按「建议奶量 + 偏好偏移」计算出的值写入
  - 若分钟级过密（与上次间隔极短）:
    - 弹出确认 Sheet，建议用户先去“今日记录”核对并撤销多余记录
    - 用户可选择“继续记录”
- 单次奶量过大（> 200ml）:
  - 必须二次确认（确认 Sheet）
- 异常提示不叠加在投喂按钮上:
  - 记录后在 Undo Toast 上以轻提示呈现（并提供“核对/说明”）
- 今日抽屉:
  - 点击 Hero 任意区域打开
- 实时同步:
  - 进入首页后连接 WebSocket（按 baby_id 订阅）
  - 收到事件后 300ms 防抖刷新 `feedings + stats`

### 5.4 今日抽屉（今日喂奶记录）

目标: 交接与核对，强调“分布与节奏”，避免信息噪音。

- 入口:
  - 首页 `今日` 按钮
  - 点击 Hero
  - 状态说明 Sheet 内链接
- 内容:
  1) 今日摘要: `次数 · 总量ml · 平均ml/次`
  2) 奶粉元信息（若已绑定）: `品牌 · 段位 · 勺数换算`
  3) 24 小时节奏轴（0-24）
     - 仅显示事件点
     - 默认高亮“最新点”（显示 label: `HH:MM · xxxml`）
     - 点击点切换 label
     - 点位聚类（例如 15 分钟内多次记录）显示一个点 + 数字计数
  4) 今日记录列表:
     - 时间（HH:MM）
     - 奶量（ml）
     - 记录人（家庭成员昵称）
     - 左滑操作: 编辑 / 删除
- 权限:
  - 成员只能编辑/删除自己创建的记录
  - 管理员可编辑/删除所有成员记录

### 5.5 喂养记录详情（编辑/删除）

目标: “就地修改”并保持 iOS 克制。

- 展示字段:
  - 时间（只读）
  - 记录人（只读）
  - 奶量（可编辑）
- 校验:
  - 奶量范围: 10-300 ml
  - >200 ml 提示确认
- 删除:
  - danger 确认 Sheet

### 5.6 状态说明 Sheet（可解释性）

目标: 解释“为什么我现在是这个状态”，只给关键对比与下一步。

内容结构:

- 当前状态（状态词 + 简短解释）
- 对比（图形化优先）:
  - 今日奶量: 当前值 vs 今日目标 + 预期值（按当天时间进度计算）
  - 近 7 天日均奶量: 当前值 vs 参考范围
- 偏好（高价值低风险补齐）:
  - 默认偏移（-20/0/+20 等少量档位，避免把首页变设置页）
  - 点击即保存（或保存按钮均可，但需保证用户理解“只影响默认显示，不自动记录”）
- 建议（最多 3 条，去重）:
  - 过密 -> “先核对撤销”
  - 超时 -> “按推荐量投喂，把节奏拉回设置”
  - 生长偏离 -> “建议咨询医生”
- Links:
  - 看今日记录 / 去数据详情 / 帮助与常见问题
- 免责声明: `仅供参考，异常请咨询医生。`

### 5.7 喂奶设置（间隔与应用内提醒）

目标: 用最简单方式让倒计时更准。

- 设置项:
  - 白天间隔（1-5 小时，默认 3）
  - 夜间间隔（3-7 小时，默认 5）
  - 白天开始/结束（默认 06:00-18:00）
  - 应用内提醒开关（默认开）
  - 提前提醒分钟数（5-30，默认 15）
- 展示:
  - 下次喂奶时间（来自后端计算）
  - 文案明确: `应用内提醒（需保持应用打开）`
- 权限:
  - 仅管理员可修改（成员只读；若尝试保存需提示无权限）

### 5.8 投喂偏好（高价值低风险补齐）

目标: 让“建议奶量”更贴近家庭习惯，同时保持简单。

- 偏移量（delta）:
  - -60 ~ +60，步长 5
  - 快捷档位 chips（例如 -40/-30/.../+40）
  - 含义说明: `首页按钮显示的默认奶量 = 系统推荐 + 你的偏移`
- 常用单次奶量（default_amount）:
  - 允许清空（表示不固定）
- 预览区:
  - `系统推荐 xxx -> 应用偏移后 yyy`
- 保存:
  - 显式保存按钮 + dirty 状态
  - “恢复默认”

### 5.9 数据详情（趋势 + 参考范围 + 明细）

目标: “只展示关键信息”，解释收纳；明细默认折叠。

- 顶部:
  - 出生 xxx（月龄）
  - 入口: 喂奶设置
- 关键 KPI（图形化，不堆文字解释）:
  - 日均增重（kg/day）+ gauge
  - 日均增高（mm/day）+ gauge
  - 近 7 天日均奶量（ml/day）+ gauge
- 参考范围:
  - 页面仅显示 `参考范围 · 点此查看`
  - 点击打开 sheet，用 RangeBar 展示「当前值 vs 参考范围」
  - 生成建议（短句）
- 明细（默认收起）:
  - 月份横向选择（最近 6 个月）
  - 表格: 日期 / 体重 / 身高 / 日总奶量
  - 空态: `本月暂无记录` + 引导补录
  - 点击某天打开编辑弹窗（upsert 体重/身高）

### 5.10 家庭共享（邀请码）

目标: “好交接”的核心能力。

- 加入家庭:
  - 输入 6 位邀请码 -> 加入并切换到该宝宝
  - 幂等: 已加入再次使用邀请码应返回成功
- 成员列表:
  - 显示头像、昵称、角色（管理员/成员）
  - 管理员可移除成员（不可移除自己）
- 邀请码:
  - 仅管理员可生成
  - 复用策略: 若存在未过期且未使用的邀请码优先复用（减少困惑）
  - 有效期: 7 天
  - 使用后失效

### 5.11 奶粉（品牌/规格/冲泡要求）

目标: 让记录与交接更“可执行”（勺数、水温、步骤），同时把未来可盈利的“推荐/购买”入口放在同频模块内（透明、可关闭、不打扰）。

#### 5.11.1 选择奶粉页（/pages/formula-select/index）

设计要点（参考 iOS Settings 的“分组列表”，避免资料库式面板）：

1) 当前使用
   - 展示：品牌 +（可选）系列/规格（age_range）
   - 入口：`冲泡要求`
   - 权限：非管理员显示 `只读` pill + 一句话说明（不让用户点到 403 才知道）

2) 搜索（管理员）
   - 支持品牌中文名 / 英文名过滤
   - 不展示冗余解释与市场份额

3) 购买偏好（管理员）
   - 选项：`官方 / 京东 / 天猫 / 拼多多`
   - 本地持久化：`buy_platform_pref`
   - 目的：先解决“去哪买”的真实痛点，并为后续 CPS/返利链接留出稳定入口

4) 推荐（管理员）
   - 默认规则：取市场热度 TopN（不做“功效”结论，避免医疗风险）
   - 副标题：最多一行（2 个特性 + 月龄段位提示）
   - 点击：直接选中品牌并自动滚动到「规格」区域，减少“下一步在哪”的迷失

5) 最近使用（管理员）
   - 本地缓存：`recent_formula_brand_ids:<babyId>`，便于快速切换（断货/转段/换配方）

6) 全部品牌（管理员）
   - 列表点选 + check 标记（比三列卡片更 iOS、也更可点）

7) 系列/冲泡规格（管理员）
   - 数据源：`GET /api/formula/specifications?brand_id=...`
   - 默认命中顺序：
     - 若已有绑定：优先命中（series_name + age_range）
     - 否则按月龄匹配（0-6 / 6-12）
     - 兜底：第一条
   - 无规格数据：允许仅绑定品牌，并提示“以包装说明为准”

8) 保存
   - 底部固定按钮保存为当前奶粉（`POST /api/babies/:id/formula`）
   - 非管理员禁止保存，点击提示“仅管理员可更换奶粉”

外链规则（购买/官网）：

- H5：直接打开外部链接（新开页）
- 其他端：复制链接到剪贴板（避免缺少 WebView 页面导致卡住）
- 若品牌无官方链接：复制品牌名，提示“去平台搜索”
- **未来若包含 CPS/返利/推广链接，必须显式标注「推广/返利」并提供关闭入口（付费版可完全隐藏）**

#### 5.11.2 冲泡要求页（/pages/formula-spec/index）

- 展示：勺数换算（ml/勺、g/勺）、水温区间、冲泡步骤、数据来源
- 兜底：无官方步骤时显示“以包装说明为准”

#### 5.11.3 商业化路线（低风险可持续）

- Phase 0（当前落地）：平台搜索/官网跳转（解决“去哪买”，不做功效宣称）
- Phase 1：服务端可配置推荐位（Server-driven）
  - 推荐位字段（建议）：`brand_id`、`label`、`priority`、`target_age_range`、`platform`、`cps_url`、`start_at/end_at`
  - 前端规则：只渲染 + 透明标注，不参与“医学/功效”推断
- Phase 2：联盟 API/手动维护价格与库存（可选）
  - 技术难点：反爬、链接有效性、合规（必须有广告标识）、归因链路
  - 风险控制：只展示“价格/可购性”与“官方规格是否完整”，不展示“更适合/更健康”等结论

### 5.12 帮助与常见问题（FAQ）

目标: 降低学习成本 + 解释性补足（替代一堆弹窗）。

建议模块:

- 30 秒上手步骤（建档 -> 投喂 -> 设置间隔）
- 推荐与提示怎么理解（推荐算法、为何提示“留意/处理”）
- 弱网/同步/排障（离线提示、token 失效）

### 5.13 数据报告（导出）

目标: 便于发给医生/家人或长期归档。

- 范围:
  - 快捷: 近 7/30/90 天
  - 自选: from/to（最多 366 天）
- 输出:
  - JSON（默认）
  - CSV（format=csv）
- 报告内容:
  - summary: 总奶量、日均、次数、单次均值、最大/最小日及日期
  - days: 每日总量、次数、体重/身高（若有）
  - by_member: 每个成员的次数与总量

### 5.14 管理后台（仅管理员）

管理员判定来自服务端环境变量 `ADMIN_USER_IDS`（逗号分隔用户 id）。

- 卫健委标准:
  - 版本列表（active_version）
  - 列表过滤: version/type/active
  - 导入 JSON（数组或对象）
  - 启用版本: 启用后其他版本全部置 inactive
- 奶粉规格维护:
  - 按品牌筛选
  - 新增/编辑规格
  - 标记已验证（verify）

---

## 6. 核心算法与规则（必须与后端一致）

### 6.1 时间与时区（硬性约束）

- 数据库存储: 所有“时间点”字段必须使用 `TIMESTAMPTZ`（带时区），避免跨设备/跨时区导致倒计时异常
- “今日”边界以用户本地时区的 00:00-24:00 计算（前后端一致）
- 对 iOS/Safari 的日期解析兼容:
  - 前端尽量使用后端返回的 `next_feeding_timestamp`（秒）而不是 `YYYY-MM-DD HH:mm:ss` 字符串
  - 若必须解析字符串，需替换空格为 `T`

### 6.2 推荐奶量（RecommendedAmount）

输入:

- baby: 月龄、体重（缺失则按月龄估算）
- 今日喂奶记录（当天 0:00-24:00）
- 喂奶设置:
  - day_start_hour/day_end_hour
  - day_interval/night_interval（小时）
- 用户偏好:
  - default_amount（可选）
- 卫健委标准:
  - milk_by_weight 推荐系数（默认 135 ml/kg/day）
  - milk_by_age 参考文案（例如 `700-900ml/天`）

计算:

1) 日目标（daily_standard）
   - `daily_standard = round(current_weight_kg * coefficient)`
   - weight 缺失则按月龄估算（WHO 常见估算）
2) 今日已喝（daily_consumed）
   - 今日所有 feedings.amount 之和
3) 今日剩余次数（remaining_times）
   - 根据当前时间与设置计算（见 6.3）
   - 最少返回 1
4) 推荐单次量（recommended）
   - 若 `daily_consumed < daily_standard`:
     - `recommended = (daily_standard - daily_consumed) / remaining_times`
     - clamp 到 `[50, 200]`
   - 否则:
     - 优先用 `default_amount`（若存在）
     - 否则 `daily_standard / 6`
5) warning（低/高）
   - ratio = `daily_consumed / daily_standard`
   - > 1.2 => `high`
   - < 0.8 => `low`
   - else `normal`

输出 JSON:

```json
{
  "recommended": 150,
  "daily_standard": 810,
  "daily_consumed": 300,
  "remaining_times": 4,
  "warning": "normal",
  "age_reference": "700-900ml/天"
}
```

### 6.3 今日剩余次数（remaining_times）

目标: 给用户一个“今天还剩几次机会把目标补齐”的直觉估计（不追求绝对精确）。

规则（按后端实现口径）:

- dayStartHour <= 当前小时 < dayEndHour: 视为白天
  - 白天剩余次数 = (dayEnd - now) / dayInterval
  - + 晚上次数 = (24 + dayStart - dayEnd) / nightInterval
- 否则视为夜间
  - 夜间剩余次数 = (24 + dayStart - now) / nightInterval
- 最少返回 1

### 6.4 下次喂奶时间（next_feeding_time）

规则（以用户直觉为准，避免跨时段“忽然变更间隔”带来困惑）:

- 以上次喂奶时间为基准:
  - 若“上次喂奶发生在白天时段” -> `next = last + day_interval`
  - 若发生在夜间时段 -> `next = last + night_interval`
- 若 next 早于当前时间（例如用户很久没记录）:
  - 以当前时间为基准，用“当前时段的 interval”往后推

后端输出需同时提供:

- `next_feeding_time`: `YYYY-MM-DD HH:mm:ss`（展示用）
- `next_feeding_timestamp`: unix 秒（强制用于前端倒计时）

### 6.5 异常/提醒规则（首页与撤销条）

目标: 识别“明显不合理”的记录或节奏，给出轻量、可执行提示。

#### 6.5.1 过密喂奶（高风险，优先级最高）

触发条件（任一满足）:

- 2 分钟内 >= 2 条记录且最小间隔 <= 2 分钟
- 10 分钟内 >= 3 条记录且最小间隔 <= 5 分钟
- 最近一次间隔 <= 2 分钟

表现:

- 记录前: 确认 Sheet（建议先核对今日记录，可继续记录）
- 记录后: Undo Toast danger 提示 + 次按钮显示“核对”

#### 6.5.2 间隔偏短（中风险）

- 最近一次间隔 <= 10 分钟（但未达到“过密”阈值）
- 表现: Undo Toast warn + “说明”

#### 6.5.3 今日明显超参考（中风险）

- `daily_consumed > daily_standard` 且超出 >= 60ml
- 表现: Undo Toast warn

#### 6.5.4 单次偏大（中风险）

- amount > 200ml
- 表现: 记录前二次确认 + 记录后 warn

### 6.6 偏好学习（best-effort）

目标: 用户每次记录都在“教系统”，但不增加用户操作。

在创建 feeding 时（后端）:

- 先计算“本次记录前的 recommended”（避免被本次 feeding 影响）
- `delta = amount - recommended`，clamp 到 [-120, 120]
- 写入 user_preferences:
  - default_amount = amount
  - adjustment_pattern = delta
  - input_method = direct/quick/manual（可选）

---

## 7. 权限与角色模型

### 7.1 家庭角色（family_members.role）

- admin: 管理员（宝宝创建者默认 admin）
- member: 成员（邀请码加入）

### 7.2 权限矩阵（必须落地到接口）

- 宝宝资料（PUT/DELETE baby）: admin only
- 喂奶设置（PUT settings）: admin only
- 选择奶粉（POST baby formula）: admin only
- 生成邀请码/移除成员: admin only
- 查看数据/创建记录:
  - feedings: 家庭成员均可创建
  - growth_records: 家庭成员均可 upsert
- 编辑/删除 feeding:
  - admin: 可编辑/删除任意成员记录
  - member: 仅可编辑/删除自己创建的记录

---

## 8. 数据模型（概念级）

### 8.1 核心实体

- User
  - phone（唯一）
  - nickname、avatar_url、password_hash
- Baby
  - user_id（owner）
  - nickname、avatar_url、birth_date、birth_time、gender
- Feeding
  - baby_id、user_id
  - amount（10-300）
  - feeding_time（TIMESTAMPTZ）
  - formula_brand_id / formula_series_name / scoops / device_id
- GrowthRecord
  - baby_id、record_date（唯一）
  - weight(kg)、height(cm)、daily_milk_amount（可选）
- FeedingSettings（宝宝级）
  - baby_id（唯一）
  - day_interval/night_interval、reminder_enabled、advance_minutes、day_start_hour/day_end_hour
- UserPreference（用户维度 + 宝宝维度）
  - user_id + baby_id（唯一）
  - default_amount、adjustment_pattern、input_method
- FamilyMember
  - baby_id + user_id（唯一）
  - role、joined_at
- InviteCode
  - code（6 位）
  - baby_id、creator_id、expires_at、used/used_by/used_at
- FormulaBrand
  - name_cn/name_en、market_share、features、official_url
- FormulaSpecification
  - brand_id、series_name、age_range
  - scoop_weight_gram、scoop_ml
  - water_temp_min/max、mixing_method、data_source、is_verified、verified_at
- HealthStandard
  - version、type、month_min/max、data(json)、is_active
- OperationLog（审计）

---

## 9. 接口契约（REST + WS）

统一约定:

- Base: `/api`
- Auth: `Authorization: Bearer <token>`
- 错误返回优先使用:
  - `{"error":"..."}`
  - 或 `{"message":"..."}`
- 401: token 失效，客户端必须清理 token 并回到登录页

### 9.1 公开接口

- POST `/api/public/register`
  - req: `{ phone, password, nickname? }`
  - resp: `{ token, user }`
- POST `/api/public/login`
  - req: `{ phone, password }`
  - resp: `{ token, user }`

### 9.2 用户

- GET `/api/user/profile` -> `{ user }`
- PUT `/api/user/avatar` req `{ avatar_url }` -> `{ user }`

### 9.3 宝宝

- GET `/api/babies` -> `{ babies: [] }`（包含我创建的 + 我加入家庭的）
- POST `/api/babies`（创建即成为 admin）
- GET `/api/babies/:id`
- PUT `/api/babies/:id`（admin only）
- DELETE `/api/babies/:id`（admin only）

### 9.4 喂养记录

- POST `/api/feedings`
  - req: `{ baby_id, amount, feeding_time? (RFC3339), formula_brand_id?, formula_series_name?, scoops?, input_method? }`
  - resp: `{ feeding }`
- GET `/api/feedings?baby_id=...&start_date=...&end_date=...`
  - resp: `{ feedings: [] }`（limit 100，按 feeding_time desc）
- GET `/api/feedings/stats?baby_id=...`
  - resp:
    - `{ stats, recommended, preference, next_feeding_timestamp? }`
- PUT `/api/feedings/:id`（本人或 admin）
- DELETE `/api/feedings/:id`（本人或 admin）

### 9.5 喂奶设置

- GET `/api/babies/:id/settings` -> `{ settings }`
- PUT `/api/babies/:id/settings`（admin only）-> `{ settings }`
- GET `/api/babies/:id/next-feeding-time` -> `{ next_feeding_time, next_feeding_timestamp }`

### 9.6 生长数据

- GET `/api/babies/:id/growth-stats` -> `{ age_in_days, current_weight, current_height, daily_weight_gain, daily_height_gain, daily_avg_milk, reference }`
- GET `/api/babies/:id/daily-records?month=YYYY-MM` -> `{ month, records }`
- POST `/api/babies/:id/growth-records`（按日期 upsert）-> `{ record }`

### 9.7 偏好

- GET `/api/babies/:id/preferences` -> `{ preference }`
- PUT `/api/babies/:id/preferences` -> `{ preference }`

### 9.8 报告

- GET `/api/babies/:id/report?from=YYYY-MM-DD&to=YYYY-MM-DD&format=json|csv`
  - resp json: `{ baby, range, summary, by_member, days }`
  - resp csv: `text/csv`

### 9.9 奶粉

- GET `/api/formula/brands` -> `{ brands }`
- GET `/api/formula/specifications?brand_id=...&series_name?&age_range?` -> `{ specifications }`
- POST `/api/babies/:id/formula`（admin only）-> `{ selection }`
- GET `/api/babies/:id/formula` -> `{ selection }`
- GET `/api/babies/:id/formula/specification` -> `{ specification }`

### 9.10 家庭

- GET `/api/babies/:id/family-members` -> `{ members }`
- DELETE `/api/babies/:id/family-members/:userId`（admin only）
- POST `/api/invite/generate`（admin only）req `{ baby_id }` -> `{ code, expires_at }`
- POST `/api/invite/use` req `{ code }` -> `{ success, baby }`

### 9.11 WebSocket（实时同步）

- GET `/ws?token=...&baby_id=...`
- 鉴权: token（query 优先，其次 Authorization header）
- 推送消息（JSON）:

```json
{
  "type": "event",
  "baby_id": 1,
  "entity": "feeding",
  "action": "create",
  "id": 123,
  "timestamp": 1730000000
}
```

客户端规则:

- 收到消息后 300ms 防抖刷新（避免短时间多次 create/update/delete）
- 刷新集合: `feedings + stats`（必要时 growth 也可刷新，但当前最小集即可）

---

## 10. 验收标准（手机端为主）

### 10.1 主链路（必过）

1) 新用户注册 -> 自动进入首页  
2) 无宝宝档案时首页展示清晰空态，引导去建档  
3) 建档只填昵称+出生日期即可成功（出生时间自动兜底）  
4) 回到首页后可一键“投喂”记录成功，出现撤销条（3 秒可撤销）  
5) 点击“今日”打开今日抽屉:
   - 有 24h 时间轴点位
   - 列表可左滑编辑/删除
6) 非管理员账号加入家庭后:
   - 可记录喂奶
   - 不能修改喂奶设置/宝宝资料/奶粉选择（应提示无权限）
7) 两台设备同时打开同一宝宝:
   - A 记录后，B 在 1 秒内自动刷新看到新记录（WS + 防抖刷新）
8) 弱网/断网:
   - 顶部出现离线提示条
   - 点击重试可恢复并触发刷新

### 10.2 关键边界（必测）

- 单次奶量输入 201ml:
  - 记录前必须二次确认
- 2 分钟内连续记录 2 次:
  - 必须出现“可能误触/记录过密”确认 Sheet
  - 记录后 Undo Toast 有 danger 级别提示与“核对”按钮
- 时区/跨日:
  - 23:30 记录后 next feeding 跨午夜，轨道 window/fill 显示正确，不出现“还剩十几个小时”的离谱倒计时
- iOS Safari:
  - 倒计时/下次喂奶时间展示正常（使用 timestamp）

---

## 11. 未来迭代（非本期，但可作为 backlog）

- Push 通知（系统级提醒）
- 多宝宝切换入口（若家庭同时有多个宝宝）
- 手动选择喂奶时间（补录/纠错）
- 记录备注（吐奶/是否安抚喂等）
- 统计图表（周/月趋势图，依然保持克制）
