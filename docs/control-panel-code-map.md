# 控制台代码地图

更新时间：2026-06-10

这份地图用于维护 `web-vue/` 新控制台和 chatgpt2api 后端之间的代码关系。它只描述当前主路径，避免后续继续把 `gemini-web2api` 的旧概念直接带进来。

## 总规则

- 页面和布局不直接请求后端；只能调用 `web-vue/src/api/*.ts` adapter 或基于 adapter 的 composable。
- `web-vue/src/api/client.ts` 是唯一 Axios 实例和 Bearer key 注入点；Header“接口信息”展示的调用密钥也必须从这里的 `getAuthToken()` 读取，不能读取 `settings.basic.api_key`。
- `web-vue/src/api/index.ts` 不导出裸 `apiClient`。
- 新代码使用 `accountsApi`；`reverseAccountsApi` 只保留兼容旧 import。
- `正常/限流/异常/禁用` 这类后端账号状态只由 `api/accounts.ts` 定义和规范化，页面只引用 adapter 类型。
- 调用日志详情只由 `api/logs.ts` 解析为 `SystemLogRow`；页面不再直接拆 `SystemLog.detail` 里的 `error_code`、`stage`、`raw_upstream_message` 等字段。
- 系统设置的默认值、可编辑形状和保存到后端的兼容 payload 只由 `api/settings.ts` 负责；页面不要手写 `basic.proxy`、`basic.base_url`、`basic.image_expire_hours` 同步逻辑。
- 代理引用语义只由 `api/proxy.ts` 负责解析和序列化：空值表示全局代理，`direct` 表示强制直连，`group:<id>` 表示代理组，`profile:<id>` 只作为旧单节点兼容引用。
- 账号编辑页不再提供旧 `profile:<id>` 选择入口；已有老账号遇到 `profile:<id>` 时只按历史兼容引用展示并保留原值。
- 前端 UI 偏好只由 `web-vue/src/lib/preferences.ts` 读写；页面和布局不要散落 `localStorage` key。`api/client.ts` 的登录 token 是认证存储，不归偏好 adapter。
- 概览中心可以放一个轻量画图面板，主导航也提供“画图”入口；创建任务必须走 `/api/image-tasks/*` 异步任务接口，不要让浏览器等待长图像请求。
- 画图页是对话工作台，不是管理页。改 `web-vue/src/views/ImageTasks.vue` 前先看原版 `web/src/app/image/page.tsx`、`components/image-composer.tsx`、`components/image-results.tsx`、`components/image-sidebar.tsx`；用户 prompt 靠右、结果靠左、底部 composer、历史侧栏和图片预览应优先复用/仿照这套结构。`image-tasks` 保持普通控制台路由，`AppShell` 的全局 header 和 sidebar 不隐藏；画图自己的历史侧栏仍由 `ImageTasks.vue` 管理。
- 画图 footer 额度优先使用 `/api/image-tasks` 响应里的 `quota_summary`，独立 `/api/image-tasks/quota` 只作为刷新/兜底接口。接口失败、非 JSON 或旧后端 HTML fallback 只能显示读取失败，不能静默归零；真实 0 必须来自后端明确的 `total_quota: 0`。
- 画图任务的 `n` 控制一次请求输出数量，范围 `1..4`，默认 `1`；多参考图输入仍由 `images`/`image`/`image_url` 负责，不能和输出数量混为一谈。
- 画图历史是本地浏览器历史，不是后端任务列表。整段对话、单轮记录和清空历史只删除 `preferences.ts` 里的本地对话与 task id；刷新时只按本地保存的 task id 拉取状态，不再全量挂回服务端旧任务。
- 画图历史的“回填提示词”只负责回填 prompt 和参考图，不自动改模型、比例、分辨率或质量；这些参数由用户当前选择决定，避免点历史记录时页面替用户切换参数。
- 有现成预览、弹窗、菜单、分页、图片卡片或结果展示组件时，先判断能否复用或抽到 `web-vue/src/components/ai` / `nanocat-ui`，不要在页面里重复手写一套相似 UI。
- 主导航当前保留：概览中心、画图、账号管理、日志管理、图片管理、代理管理、系统设置；监控状态和文档教程保留路由但不进主导航。
- `authStore` 必须保留 `/auth/status` 返回的 `role`。`admin` 可以进入完整控制台；`user` 登录后只进入画图页，侧边栏只显示“画图”，管理类路由应重定向回画图页。
- 调试中心作为底部工具入口恢复，覆盖搜索、Skills 搜索、PPT 生成、PSD 生成、对话等旧 `web/src/app/debug` 能力；真实调用仍按风险等级处理。
- 日志管理里的运行日志按容器/终端输出形态展示，不再用业务调用日志表格样式。
- 图片管理主界面只做图片浏览、筛选、分页、预览、标签和选择操作；保留策略、存储维护和存储进度条不在主界面展示，后端维护接口先保留。
- 真实导入、刷新账号、代理测试、WebDAV/R2 测试、删除/清理类动作都有副作用；smoke 前需要明确测试对象。

## 当前主入口

```text
main.py
  -> api/app.py
    -> api/ai.py            OpenAI 兼容接口和图片协议入口
    -> api/accounts.py      账号池、账号组、OAuth、CPA、Sub2API
    -> api/image_tasks.py   异步图片任务
    -> api/system.py        管理台系统、Dashboard、日志、图片、代理、设置
```

## 前端 API Adapter 地图

| 页面/区域 | 主文件 | Adapter | 后端接口 |
| --- | --- | --- | --- |
| 登录 | `web-vue/src/views/Login.vue` | `api/auth.ts` | `POST /auth/login`, `GET /auth/status` |
| Shell/Header | `web-vue/src/layouts/AppShell.vue` | `api/client.ts`, `api/version.ts`, `api/models.ts`, `useModelCatalog.ts` | `GET /version`, `GET /api/model-catalog`；当前调用密钥来自本地 Bearer token |
| 概览中心 | `web-vue/src/views/Dashboard.vue`, `views/dashboard/useDashboardPage.ts` | `api/stats.ts`, `api/imageTasks.ts` | `GET /api/dashboard`, `/api/image-tasks/*` |
| 账号管理 | `web-vue/src/views/Accounts.vue`, `views/accounts/useAccountsPage.ts` | `api/accounts.ts`, `api/accountImports.ts`, `api/proxy.ts` | `/api/accounts*`, `/api/account-groups`, `/api/cpa/*`, `/api/sub2api/*`, `/api/proxy/groups*` |
| 日志管理 | `web-vue/src/views/Logs.vue` | `api/logs.ts` | `GET /api/logs`, `GET /api/runtime-logs`, `POST /api/logs/delete` |
| 图片管理 | `web-vue/src/views/Gallery.vue` | `api/gallery.ts`, `api/settings.ts` | `/api/images*`, `/images/*`, `/image-thumbnails/*`, `/api/images/storage*` |
| 代理管理 | `web-vue/src/views/Proxy.vue` | `api/proxy.ts`, `api/settings.ts` | `/api/proxy/groups*`, `/api/proxy/test`, `/api/settings` |
| 系统设置 | `web-vue/src/views/Settings.vue` | `api/settings.ts`, `api/accountImports.ts`, `api/userKeys.ts` | `/api/settings`, `/api/backups*`, `/api/image-storage/*`, `/api/cpa/*`, `/api/sub2api/*`, `/api/auth/users*` |
| 接口文档 | `web-vue/src/views/Docs.vue` | `api/models.ts`, `useModelCatalog.ts` | `GET /api/model-catalog`，保留隐藏路由 |
| 画图 / 图片任务 | `web-vue/src/views/ImageTasks.vue` | `api/imageTasks.ts` | `/api/image-tasks/*`，主导航入口，普通 user key 的唯一控制台页面；UI 对齐原版 `web/src/app/image` 对话工作台 |
| 调试中心 | `web-vue/src/views/DebugCenter.vue` | `api/debug.ts` | `/v1/search`, `/v1/chat/completions`, `/v1/ppt/generations`, `/v1/psd/generations`, `/v1/editable-file-tasks` |

## Backend Contract 地图

| 领域 | 路由文件 | 服务文件 | 存储/状态 |
| --- | --- | --- | --- |
| 账号池和账号组 | `api/accounts.py` | `services/account_service.py`, `services/oauth_login_service.py`, `services/cpa_service.py`, `services/sub2api_service.py` | 账号默认 `data/accounts.db`；账号组在 `config.json.account_groups` |
| 模型目录 | `api/system.py` | `services/model_catalog_service.py` | 只读聚合，来自配置和账号池，不访问上游 |
| Dashboard | `api/system.py` | `services/account_service.py`, `services/log_service.py`, `services/image_service.py`, `services/config.py` | 实时聚合，不单独保存看板数据 |
| 调用日志 | `api/system.py` | `services/log_service.py` | `data/logs.jsonl` |
| 运行日志 | `api/system.py` | `services/runtime_log_service.py` | 内存 logger + 常见日志文件 |
| 图片管理 | `api/system.py` | `services/image_service.py`, `services/image_storage_service.py`, `services/image_tags_service.py` | 原图目录/WebDAV、`image_index.json`、`image_tags.json` |
| 图片任务 | `api/image_tasks.py` | `services/image_task_service.py`, `services/protocol/*` | `data/image_tasks.json` |
| 代理组 | `api/system.py` | `services/proxy_service.py`, `services/config.py` | `config.json.proxy_groups`；旧 `proxy_profiles` 仅兼容 |
| 设置/备份 | `api/system.py` | `services/config.py`, `services/backup_service.py` | `config.json`, `data/backup_state.json` |
| 用户密钥 | `api/accounts.py` | `services/auth_service.py` | `data/accounts.db` 的 `auth_keys` 表，或当前 storage backend 的 auth key 存储 |

## Backend Proxy 链路地图

| 链路 | 当前入口 | 代理来源 |
| --- | --- | --- |
| ChatGPT 主对话/图片会话 | `services/openai_backend_api.OpenAIBackendAPI.session` | 账号 proxy > 账号组代理组 > 全局 proxy > 直连 |
| Codex 图片 responses | `OpenAIBackendAPI.iter_codex_image_response_events` | 复用 `OpenAIBackendAPI.session`，不再使用 `urllib.request` |
| access token 刷新 | `services.account_service._request_access_token_refresh` | 当前账号 proxy/账号组/全局 proxy |
| 密码重登 OAuth | `services.account_service._login_with_password` | 全局 proxy > 直连 |
| 图片 URL 输入下载 | `api.image_inputs` | 全局 proxy > 直连 |
| 内容过滤 | `services.content_filter` | 全局 proxy > 直连 |
| OAuth 登录回填 | `services.oauth_login_service` | 全局 proxy > 直连 |
| CPA / Sub2API 远程读取 | `services.cpa_service`, `services.sub2api_service` | 全局 proxy > 直连 |
| 微软/webfree 注册机 | `services/register/*` | 注册机独立代理配置，不跟账号代理组混用 |

## Backend Contract Test 地图

| 契约 | 测试文件 | 锁定行为 |
| --- | --- | --- |
| 账号列表/账号组 | `test/test_accounts_api.py` | 服务端分页筛选、轻量创建刷新、账号组后端计数、缺失代理组失败、重复名称失败、删除账号组清空账号绑定 |
| 账号存储后端 | `test/test_database_storage.py`, `test/test_storage_backend.py`, `test/test_account_invalid_removal.py` | SQLite 增量 upsert/delete、按状态删除、单账号 token 替换、分页统计、异常账号确认后移除 |
| 代理解析 | `test/test_proxy_service.py` | 显式代理、账号代理、`direct`、`group:<id>`、账号组默认代理组、全局代理和直连的优先级；代理组跳过禁用/冷却节点；旧 `profile:<id>` 兼容 |
| 代理组接口 | `test/test_system_api.py` | 旧 profile 兼容接口、代理组创建/列表/删除、代理组节点测试写回健康字段 |
| Codex responses transport | `test/test_codex_responses_transport.py` | Codex 图片 responses 复用已配置代理的 `OpenAIBackendAPI.session`，HTTP 错误保留 status/body/retry_after |

默认本地回归命令是 `python -m unittest discover -s test`。真实 localhost/上游 smoke 默认跳过，必须设置 `CHATGPT2API_RUN_LIVE_HTTP_TESTS=1` 才运行；测试辅助模块使用 `test/helpers.py`，不要新增 `test/utils.py`，否则会遮蔽项目自己的 `utils` 包。

## 账号 Adapter 收口

当前账号前端主模块是：

```text
web-vue/src/api/accounts.ts
```

它负责把后端 `BackendAccount` 转成前端账号列表模型，并封装分页、账号组、刷新进度、重登进度、导入、导出、启用、禁用、删除和绑定账号组。

账号页仍然可以显示和编辑后端状态，但状态接口从这里导出：

```ts
AccountBackendStatus
ACCOUNT_BACKEND_STATUS_VALUES
normalizeAccountBackendStatus(...)
```

这样页面不用自己维护 `正常/限流/异常/禁用` 的合法值。

兼容入口：

```text
web-vue/src/api/reverseAccounts.ts
```

这个文件只做 re-export。后续新代码不要再从它 import。

兼容类型：

```ts
ReverseAccount -> Account
ReverseLane -> AccountLane
ReverseAccountsResponse -> AccountsResponse
```

保留原因：部分旧组件或外部引用可能还没清理，先不做破坏性改名。

## 日志 Adapter 收口

当前日志前端主模块是：

```text
web-vue/src/api/logs.ts
```

它负责三层输出：

- `listSystem(...)`：服务端分页调用日志，返回 `SystemLogsResponse`。
- `listRuntime(...)`：运行日志，返回 `RuntimeLogsResponse`。
- `normalizeSystemLogRow(...)`：把后端 `SystemLog.detail` 转成页面可直接使用的 `SystemLogRow`，包括诊断 chip、预览图 URL、耗时、错误码、上游文本和原始 JSON。

`web-vue/src/views/Logs.vue` 只保留筛选、分页、导出、弹窗和显示逻辑；如果后端日志字段变动，优先改 `api/logs.ts`。

调用日志底部分页复用：
```text
web-vue/src/components/ai/ListPagination.vue
```

页数按 `SystemLogsResponse.total` 和当前 `filters.limit` 计算，不再在页面层用 `has_more` 自己维护上一页/下一页按钮。

## 设置 Adapter 收口

当前设置前端主模块是：

```text
web-vue/src/api/settings.ts
```

它负责三件事：

- `normalizeSettings(...)`：把后端 `config.json` 的宽松对象补成前端稳定 `Settings`。
- `prepareSettingsForEdit(...)`：给页面一份可安全编辑的标准形状。
- `prepareSettingsForSave(...)`：保存前统一补齐后端兼容字段，尤其是顶层 `proxy/base_url/image_retention_days` 和旧 `basic.proxy/basic.base_url/basic.image_expire_hours`。

`Settings.vue`、`Proxy.vue`、`Gallery.vue` 不再直接维护旧 `basic.*` 同步规则。后续新增设置项时，先改 `api/settings.ts`，再让页面绑定标准字段。

## 代理 Adapter 收口

当前代理前端主模块是：

```text
web-vue/src/api/proxy.ts
```

它负责代理组接口和代理引用语义：

```ts
parseProxyReference(...)
serializeProxyReference(...)
proxyReferenceLabel(...)
```

页面层可以展示、选择和测试代理，但不要自己解析 `direct`、`group:`、`profile:` 前缀。账号页、账号列表显示和代理页都应复用这些 helper。

新控制台前台只引导使用代理组。旧 profile API 和 `profile:<id>` 解析保留在 adapter/后端用于历史数据兼容，不再出现在账号编辑的代理模式选项里。

## 图片管理 Adapter 收口

当前图片管理前端主模块是：

```text
web-vue/src/api/gallery.ts
```

它负责图片列表、标签、服务端分页字段映射，以及资源 URL 规则：

```ts
resolveGalleryFileUrl(...)
```

`Gallery.vue` 可以调用这个 helper 展示、下载、复制图片链接，但不要自己拼 `VITE_API_URL`、`window.location.origin`、`/images/` 或 `/image-thumbnails/`。

图片管理的服务端分页展示复用：
```text
web-vue/src/components/ai/ListPagination.vue
```

`Gallery.vue` 只负责传入 `currentPage`、`pageSize`、`totalItems` 和允许的 page size，不再维护自己的分页按钮和分页样式。

## 前端偏好 Adapter 收口

当前前端偏好主模块是：

```text
web-vue/src/lib/preferences.ts
```

它负责浏览器本地 UI 偏好：

- 侧边栏折叠状态。
- 账号列表视图模式和每页数量。
- 调用日志、运行日志每页数量。
- 图片管理每页数量。
- 公开日志折叠状态。
- 隐藏的图片任务本地 ID 列表。
- 画图页是否隐藏服务端历史自动挂回。

页面层不再直接读写这些 `localStorage` key。当前扫描结果里，`web-vue/src/api/client.ts` 仍直接使用 `localStorage` 保存登录 token，这是认证存储，刻意不迁入偏好 adapter。

## 前端偏好和真实数据

真实数据来源见 `docs/data-storage-map.md`。当前需要记住：

- 账号池：SQLite。
- 账号组、代理组、系统设置：`config.json`。
- 调用日志：JSONL。
- 图片原图和索引：文件目录、WebDAV、图片索引 JSON。
- 概览中心：实时聚合。
- 前端 page size、侧边栏折叠、运行日志 limit、画图本地隐藏历史等：浏览器 `localStorage`，通过 `web-vue/src/lib/preferences.ts` 统一读写；换浏览器不会保留。

## 前端 UI 组件收口

当前已收口到项目内组件的通用 UI：

复用优先规则：新增或调整页面 UI 前，先检查 `web-vue/src/components/ai`、`web-vue/src/components/ui` 和 `nanocat-ui` 是否已有同类组件。能通过 props/slot 小幅扩展复用的，优先扩展原组件；只有语义、交互或数据边界明显不同，才新建组件。新建组件时必须在本表写清楚“为什么不能复用已有组件”，避免日志、图片、账号、代理页各自写一套外观。

| 组件 | 文件 | 当前使用页 | 约束 |
| --- | --- | --- | --- |
| 动作行 | `web-vue/src/components/ai/ActionRow.vue` | `Gallery.vue`, `Proxy.vue` | 只管按钮/输入的 flex、gap、对齐和移动端拉伸；保存、清理、批量下载、代理测试等业务动作仍留在页面 |
| 概览统计卡 | `nanocat-ui` `StatCard` | `Dashboard.vue` | 概览中心顶部卡片直接复用原版 `StatCard`，图标保持右上角小圆形徽标；页面只传 label/value/caption/icon/iconBg/iconColor，不再用 `MetricStrip` 的 right-icon 变体重做这一块 |
| 指标卡片组 | `web-vue/src/components/ai/MetricStrip.vue` | `Accounts.vue`, `Logs.vue`, `Gallery.vue`, `PublicLogs.vue` | 页面只传 `items`、列数、密度、图标信息和可选 valueStyle；卡片保持接近原版 `rounded-2xl` 的 16px 圆角；不要在页面层重新写 `log-stat-*`、`gallery-stat-*`、进度小卡或 `ui-card-sm` 这类局部统计卡样式 |
| 进度条 | `web-vue/src/components/ai/ProgressBar.vue` | `Accounts.vue` | 只管 0-100 百分比进度条的高度、圆角、背景、主色填充、动画和 aria 属性；百分比计算、批量停止、账号刷新和账号批量动作仍留在页面 |
| 状态徽标 | `web-vue/src/components/ai/StateBadge.vue` | `Accounts.vue`, `Logs.vue`, `Proxy.vue` | 只管小型状态文字的 tone、size、shape、border 和颜色；账号/日志/代理状态判断、文案和所有动作仍留在页面或 adapter |
| 元信息标签 | `web-vue/src/components/ai/MetaChip.vue` | `AppShell.vue`, `AccountSelectionSummary.vue`, `Docs.vue`, `Logs.vue`, `Gallery.vue`, `ImageTasks.vue`, `LogImagePreviewCell.vue` | 作为 `nanocat-ui` `MetaChip` 的薄适配层，只管模型名、版本号、账号选择计数、日志类型/来源、图库占用和图片数量这类弱信息标签的 size/tone 别名；标签内容、模型目录、账号/日志/图库数据和所有动作仍留在页面 |
| 筛选工具条 | `web-vue/src/components/ai/FilterToolbar.vue` | `Accounts.vue`, `Logs.vue`, `Gallery.vue` | 只管布局、间距、顶部边线和窄屏拉伸/堆叠；搜索、日期、下拉菜单和业务筛选状态仍留在页面 |
| 日期范围输入 | `web-vue/src/components/ai/DateRangeInputs.vue` | `Logs.vue`, `Gallery.vue` | 只管两个日期输入和“至”分隔符的布局；页面用 CSS 变量控制宽度，不在页面里重复写日期输入 DOM |
| 面板标题栏 | `web-vue/src/components/ai/PanelHeader.vue` | `Logs.vue`, `Gallery.vue`, `Proxy.vue`, `Docs.vue` | 只管标题、副信息和右侧动作按钮的 flex 布局；页面保留按钮动作和业务状态 |
| 分页 | `web-vue/src/components/ai/ListPagination.vue` | `Accounts.vue`, `Logs.vue`, `Gallery.vue` | 页码、page size 和 total 从 adapter/页面状态传入；页面不再各自维护分页按钮样式；page size 菜单默认向下打开 |
| 表格外壳 | `web-vue/src/components/ai/TableShell.vue` | `Accounts.vue`, `Logs.vue`, `Proxy.vue` | 只管表格横向滚动、滚动条口径和可选 footer 区域；列宽、表头、行、空态、分页组件和业务动作仍由页面传入 |
| 浮层菜单 | `web-vue/src/components/ai/FloatingActionMenu.vue` | 账号页菜单、日志筛选、运行日志筛选、行内更多 | 菜单宽度、分割线、hover/selected 圆角由组件控制；分组优先用 `actionMenuGroups()` 生成 |
| 表单分组 | `web-vue/src/components/ai/FormSection.vue` | `Accounts.vue`, `Proxy.vue` | 只管表单分组的边框、圆角、背景、padding、标题、actions 插槽、密度和 `surface`；字段、校验、测试、保存、导入和代理动作仍留在页面 |
| 服务状态卡 | `web-vue/src/components/ai/ServiceStatusCard.vue` | `Monitor.vue`, `PublicUptime.vue` | 只管服务状态卡、状态 badge、心跳条和 tooltip 展示；轮询、接口请求、状态映射和空态仍由 `useUptimeStatus` 和页面负责 |
| 导入模式说明 | `web-vue/src/components/ai/ImportModePanel.vue` | `Accounts.vue` | 只管账号导入弹窗内每种导入方式的标题和说明卡片；OAuth URL、文本框、文件读取、远程 CPA/Sub2API 列表和导入动作仍留在页面 |
| 可选择列表面板 | `web-vue/src/components/ai/SelectableListPanel.vue` | `Accounts.vue` | 只管远程导入列表这类可滚动选择区域的边框、高度、行间距、hover 和空态；远程读取、勾选集合、进度和导入请求仍留在页面 |
| 只读信息卡 | `web-vue/src/components/ai/InfoCard.vue` | `Docs.vue`, `Accounts.vue`, `PublicLogs.vue` | 只管文档/说明类只读卡片、账号组列表项、OAuth 授权 URL 外壳和公开日志说明条这类展示卡片的边框、圆角、背景、padding、标题、说明和 actions 插槽；表单、导入流程、日志详情和真实动作不迁入 |
| 代理节点摘要卡 | `web-vue/src/components/ai/ProxyNodeSummaryCard.vue` | `Proxy.vue` | 只管代理组表格里的节点名、启用状态、URL 脱敏和紧凑卡片样式；节点健康、测试、启停、删除、保存和确认弹窗仍留在 `Proxy.vue` |
| 代码展示块 | `web-vue/src/components/ai/CodeBlock.vue` | `Docs.vue` | 只管 curl/API 示例的 `pre/code` 展示壳、等宽字体、滚动条、边框和圆角；示例内容、模型默认值和接口说明仍由 `Docs.vue` 生成 |
| 详情字段卡 | `web-vue/src/components/ai/DetailFieldCard.vue` | `Logs.vue` | 只管日志详情抽屉里标签/值/复制按钮的只读字段展示，支持卡片和紧凑 row 变体；row 变体不显示内联复制按钮，避免字段区过挤；字段分组、空诊断字段过滤、复制实现、日志详情解析和删除动作仍留在页面与 adapter；日志页主操作区不再提供清空入口 |
| 详情图片预览 | `web-vue/src/components/ai/DetailImagePreview.vue` | `Logs.vue` | 只管日志详情抽屉里结果图片的标题、数量、缩略图网格、文件名和坏图兜底展示；点击后的大图遮罩不在这里另写，复用 `GalleryLightbox.vue`；图片 URL 整理、坏图状态、打开详情和日志动作仍留在页面 |
| 日志图片单元格 | `web-vue/src/components/ai/LogImagePreviewCell.vue` | `Logs.vue` | 只管调用日志表格图片列里的首图缩略图、坏图兜底、图片数量和空状态；图片 URL 解析、坏图集合、打开详情和日志动作仍留在页面 |
| 图库图片卡片 | `web-vue/src/components/ai/GalleryImageCard.vue` | `Gallery.vue` | 只管图库网格单张图片的缩略图/兜底、选中/过期状态、悬浮按钮、文件信息、倒计时和标签展示；筛选、分页、预览、复制、下载、删除、标签编辑和坏图状态仍留在页面 |
| 图库预览大图 | `web-vue/src/components/ai/GalleryLightbox.vue` | `Gallery.vue`, `Logs.vue` | 只管图片大图预览的 Teleport 遮罩、大图布局、关闭按钮和可选动作按钮展示；Gallery 展示下载/复制/标签，Logs 复用同一组件但只开放下载/复制，不开放标签编辑；当前预览文件、URL 格式化、下载、复制、标签编辑和图片变更动作仍留在页面 |
| 图库标签弹窗 | `web-vue/src/components/ai/GalleryTagEditorModal.vue` | `Gallery.vue` | 只管图库标签编辑弹窗的外壳、缩略图、输入框布局、已有标签 chip 和底部按钮展示；草稿状态、标签解析、保存请求、关闭保护和图片状态同步仍留在页面 |
| 详情文本块 | `web-vue/src/components/ai/DetailTextBlock.vue` | `Logs.vue` | 只管日志详情抽屉里请求文本、错误、上游文本回复、结果 URL 和 raw JSON 的长文本展示、tone、高度和复制按钮；内容来源、复制实现、日志解析和日志删除仍留在页面与 adapter |
| 选择批量条 | `web-vue/src/components/ai/SelectionBulkBar.vue` | `AccountBulkBar.vue`, `Gallery.vue` | 固定底部批量选择条只管定位、圆角、阴影、动效和移动端形态；批量菜单、下载、删除、取消等动作留在页面/业务组件 |
| 弹窗外壳 | `web-vue/src/components/ai/ModalShell.vue` | `AppShell.vue`, `Accounts.vue`, `Logs.vue`, `Proxy.vue`, `Gallery.vue` | 只管 Teleport、遮罩、z-index、居中/右侧 placement、最大宽度、面板圆角和阴影；表单内容、保存、关闭和确认逻辑留在页面 |
| 弹窗标题栏 | `web-vue/src/components/ai/ModalHeader.vue` | `AppShell.vue`, `Accounts.vue`, `Logs.vue`, `Proxy.vue`, `Gallery.vue` | 只管弹窗/抽屉标题、副标题、右侧 actions 和关闭按钮布局；关闭禁用态由页面传入，保存、导入、停止、测试等动作仍留在页面 |
| 弹窗底部操作栏 | `web-vue/src/components/ai/ModalFooter.vue` | `AppShell.vue`, `Accounts.vue`, `Proxy.vue`, `Gallery.vue` | 只管弹窗底部按钮行的 border、padding、gap 和对齐；保存、清空、关闭等动作仍由页面按钮自己处理 |
| 页面面板 | `web-vue/src/components/ai/PagePanel.vue` | `Accounts.vue`, `Proxy.vue`, `Settings.vue`, `Logs.vue`, `Gallery.vue`, `Docs.vue` | 只管 `ui-panel` 外壳和 flush 列表块的 padding/overflow；标题、筛选、表格、网格、分页和动作仍留在页面 |
| 状态块 | `web-vue/src/components/ai/StateBlock.vue` | `Accounts.vue`, `Proxy.vue`, `Settings.vue`, `Gallery.vue` | 只管加载/空态/失败提示块的边框、圆角、背景、padding、虚线、紧凑密度和可选 media 图标/加载圈插槽；业务文案、按钮、重试动作和表格内 `EmptyState` 仍留在页面 |
| 展示表面块 | `web-vue/src/components/ai/SurfaceBox.vue` | `Accounts.vue` | 只管小型只读展示块的边框、圆角、背景、密度、等宽文本、滚动和换行；表单字段、按钮、保存、导入、刷新、代理测试等动作不迁入 |

2026-06-06 已把 Logs、Gallery 和 PublicLogs 的顶部指标卡片统一到 `MetricStrip.vue`。本次验证：`npm run build` 通过；浏览器只读 smoke 覆盖 `#/logs`、`#/gallery` 和 `#/public/logs`，均无横向溢出、控制台 error 为 0，旧 `log-stat-*` / `gallery-stat-*` / PublicLogs `.ui-card-sm` DOM 已清零。PublicLogs 的后端负载颜色通过 `valueStyle` 传入，不再在页面层手写统计卡 DOM。2026-06-08 又把 Dashboard 顶部统计卡改回原版 `nanocat-ui StatCard`，避免 `MetricStrip` 的 right-icon 变体把概览图标放大或偏离原版位置；其它 `MetricStrip` 卡片圆角保持 16px。

Accounts 批量进度弹窗已统一到 `ProgressBar.vue`。它只接收页面传入的百分比并做 clamp、aria 和视觉展示，不读取账号进度数据，也不触发刷新、重登、删除、保存或任何后端写入。Gallery 主界面不再展示存储占用进度条，避免把静态容量信息误看成可执行进度。

Logs 和 Gallery 的删除/下载反馈使用 `OperationProgressModal.vue`，但它们调用的是一次性删除/下载接口，只能标记“已提交/已处理”，不能像 Accounts 批量刷新/重登那样逐批停止。若后续要给图片和日志增加停止能力，需要后端先提供 job/progress/cancel 语义。

Accounts 账号组列表、Proxy 代理组列表、Logs 调用日志状态和运行日志等级已统一到 `StateBadge.vue`。页面仍负责把后端状态映射成 `success/danger/warning/muted`；组件只负责显示，不读取日志、账号或代理数据，也不触发删除、导出、刷新、保存或代理测试。

AppShell 版本号和接口信息模型标签、Accounts 选择摘要计数、Docs 模型/风险/验收标签、Logs 调用类型/运行来源、Gallery 存储占用提示、旧 ImageTasks 任务元信息和日志图片数量已统一到 `MetaChip.vue`。它只作为 `nanocat-ui` `MetaChip` 的薄适配层，负责把本项目常用的 `xs/default/muted` 口径映射到现有组件，不读取模型目录、账号、日志、图片或任务数据，也不触发接口信息复制、账号选择、日志详情、图库维护或图片任务动作。

同日继续把 Logs、Gallery 的筛选区外层统一到 `FilterToolbar.vue`。它不接管业务值，只统一 flex、gap、border 和移动端布局口径；随后 Accounts 顶部两行工具栏的筛选区、账号组绑定区、导入/批量/导出区和低优先级刷新区也改用同一个布局壳。

Logs 和 Gallery 的日期范围输入已统一到 `DateRangeInputs.vue`。它只负责双日期输入、分隔符和移动端宽度；日志页和图片页保留自己的筛选状态与宽度变量。

Logs 和 Gallery 的标题栏已统一到 `PanelHeader.vue`。它只管标题、副信息和 actions 插槽布局，不接管刷新、导出、删除、视图切换等动作。

Gallery 的列表批量操作行已统一到 `ActionRow.vue`。保留策略、存储维护和存储进度条已从图片管理主界面移除；后续如需恢复维护入口，应独立成专项维护页或确认弹窗，不混在图片浏览主流程里。

Gallery 和账号页底部批量选择条已统一到 `SelectionBulkBar.vue`。`AccountBulkBar.vue` 现在只负责账号批量菜单和取消动作，`Gallery.vue` 只负责下载 zip、删除和取消动作；底部固定定位、圆角、阴影、动效和移动端形态不再由页面私有 CSS 维护。

账号编辑弹窗里的基础信息、Access Token 和调度属性已迁到 `FormSection.vue`。它只收口重复的内层表单卡片外壳；账号导入弹窗里的 OAuth、Access Token、Session JSON、Codex JSON、CPA JSON、远程 CPA 和 Sub2API 标题说明卡片已迁到 `ImportModePanel.vue`。OAuth 授权 URL 的展示外壳已迁到 `InfoCard.vue`，但 URL 内容、复制、再次打开、重新生成、完成导入仍保留在 `Accounts.vue`，因为它们是业务内容或会触发真实动作。

账号导入弹窗里的远程 CPA 文件列表和 Sub2API 账号列表已进一步迁到 `SelectableListPanel.vue`。它只统一列表外壳、空态、滚动高度和行样式；加载远程 CPA/Sub2API、复选状态、导入进度和真实导入请求仍由 `Accounts.vue` 控制，并继续受确认弹窗保护。

Proxy 全局代理输入和全局测试结果卡片也已迁到 `FormSection.vue`，并通过 `surface="background"` 区分只读结果块。代理组弹窗里的单个代理节点编辑行也使用 `FormSection surface="background"`；外层“代理节点”区域只保留轻量标题和列表，不再做卡片套卡片。代理组表格里的节点摘要展示已迁到 `ProxyNodeSummaryCard.vue`，用于统一节点名、状态和脱敏 URL 的紧凑展示。`Proxy.vue` 仍负责保存、清空、外部代理测试、节点检测、节点删除、代理组增删改和所有确认逻辑，`FormSection` 和 `ProxyNodeSummaryCard` 都不承载任何真实动作。

Docs 页里的认证方式、模型目录、运维边界、风险说明、验收状态和画图任务提示已迁到 `InfoCard.vue`。它只用于只读说明卡，避免把文档卡片、表单分组、导入模式说明和日志详情动态内容混成一个过宽组件；Docs 的 curl 代码块已单独迁到 `CodeBlock.vue`，不和普通信息卡混用。

Accounts 账号组管理弹窗里的账号组列表项也已迁到 `InfoCard.vue`。它只替代重复的列表卡片外壳；账号组创建表单、编辑/删除按钮、保存请求和删除确认仍留在 `Accounts.vue`。

PublicLogs 的“展示最近 N 条会话日志 / 开始对话”说明条也已迁到 `InfoCard.vue`。它只替代只读说明条的圆角边框外壳；公开日志自动刷新、折叠状态、统计数据和聊天链接仍留在 `PublicLogs.vue`。

Accounts 的批量进度弹窗已把“指标 / 状态”这组紧凑展示迁到 `MetricStrip.vue`。进度百分比、停止按钮、错误提示、批量动作和所有账号请求仍留在 `Accounts.vue`；默认只做构建和只读 smoke，不为了看这个条件块触发真实批量刷新。

Accounts 的代理模式提示、当前代理摘要、账号组启用开关外壳、OAuth 授权 URL 文本块和批量进度错误提示已迁到 `SurfaceBox.vue`。它只收口这些小型只读展示表面的 border/radius/background/padding/scroll/mono/wrap 口径；代理模式切换、账号组保存、OAuth 生成/完成、复制、重新打开、刷新进度和停止逻辑仍留在 `Accounts.vue`。

Logs 日志详情抽屉里的字段展示已迁到 `DetailFieldCard.vue`。这个组件只接收 `label/value/copyable/variant` 并向外抛出 `copy`，不读取日志结构，也不触发删除、清空、导出或任何后端写入。`Logs.vue` 负责把字段拆为“关键信息”和“诊断字段”，成功日志里为空的诊断字段不渲染，避免一屏 `-`。

Logs 日志详情抽屉里的图片预览网格已迁到 `DetailImagePreview.vue`。这个组件只展示图片数量、缩略图、文件名和坏图兜底；`Logs.vue` 仍负责把日志 URL 整理成图片项、记录坏图 URL、打开详情和所有日志动作。

Logs 调用日志表格里的图片列已迁到 `LogImagePreviewCell.vue`。这个组件只展示首图缩略图、坏图兜底、图片数量和空状态；`Logs.vue` 仍负责判断坏图 URL、打开详情抽屉和所有日志动作。

Gallery 图片网格里的单张卡片已迁到 `GalleryImageCard.vue`。这个组件只展示缩略图/无法预览兜底、选中/过期状态、悬浮操作按钮、文件名、尺寸、倒计时和标签；`Gallery.vue` 仍负责加载图片、服务端分页、筛选、选择集合、预览 lightbox、复制、下载、删除、标签编辑和坏图集合。

Gallery 图片预览大图已迁到 `GalleryLightbox.vue`。这个组件只展示 Teleport 遮罩、大图、关闭按钮、文件元信息和下载/复制/标签按钮；`Gallery.vue` 仍负责当前预览文件、图片 URL 格式化、下载触发、复制链接、打开标签编辑器，以及所有删除、清理、压缩、保存等真实动作。

Gallery 标签编辑弹窗已迁到 `GalleryTagEditorModal.vue`。这个组件只展示 `ModalShell + ModalHeader + ModalFooter` 组合、缩略图、标签输入框、已有标签 chip 和清空/保存按钮；`Gallery.vue` 仍负责标签草稿、标签解析、切换标签、关闭保护、保存请求、刷新标签列表、同步预览文件，以及所有图片删除、清理、压缩等真实动作。

Gallery 的加载、空态和加载失败提示已迁到 `StateBlock.vue`。这个组件现在通过可选 `media` 插槽承载 spinner 或空态图标；`Gallery.vue` 仍负责是否加载过、是否有文件、失败文案和页面内最小高度，不接管任何刷新、清理、压缩、删除或标签保存动作。

Logs 日志详情抽屉里的请求文本、错误、上游文本回复、结果 URL 和 raw JSON 长文本块已迁到 `DetailTextBlock.vue`。这个组件只收口标题、tone、长文本滚动、高度和复制按钮；`Logs.vue` 仍负责选中日志、复制函数、日志解析和所有日志动作。

Proxy 的代理组弹窗、Gallery 的标签编辑弹窗、Logs 的日志详情抽屉、Header 的接口信息弹窗，以及 Accounts 的账号编辑、账号组管理、导入和批量进度弹窗都已迁到 `ModalShell.vue`。其中确认弹窗仍保留在 `AppConfirmDialog.vue`，因为它需要比业务弹窗更高的 z-index，用于覆盖删除、保存等二次确认；Gallery 的图片预览 lightbox 也暂时保留为专用媒体预览。

上述业务弹窗/抽屉的标题区域已继续收口到 `ModalHeader.vue`。页面只传 title、subtitle、closeDisabled 和 actions 插槽；表单主体、footer、保存/停止/导入逻辑不进入标题组件。后续新增普通业务弹窗时，默认使用 `ModalShell + ModalHeader`，除非是确认框或媒体预览这类特殊弹窗。

上述普通业务弹窗的底部操作区域已继续收口到 `ModalFooter.vue`。当前已覆盖账号编辑保存、代理组取消/保存、图片标签清空/保存和 Header API 信息确认；导入弹窗内部各模式的局部按钮行暂不迁入，因为它们是表单分段动作，不是整个弹窗 footer。后续新增普通业务弹窗时，默认组合为 `ModalShell + ModalHeader + ModalFooter`。

Accounts、Proxy、Settings、Logs、Gallery、Docs、PublicLogs、PublicUptime 和 Monitor 的页面级 `section.ui-panel` 已迁到 `PagePanel.vue`。它只替代重复的面板外壳和 `!p-0 overflow-hidden` flush 写法，不接管标题、筛选、表格、网格、分页或真实动作。

Accounts、Proxy、Settings 和 Gallery 的部分页面级加载/空态块已迁到 `StateBlock.vue`。当前只替代重复的边框、圆角、padding、dashed 样式和可选 media 图标/加载圈位；表格单元格里的 `EmptyState` 仍保留原组件，避免破坏表格行/列语义。

Accounts、Logs 和 Proxy 的表格横向滚动外壳已迁到 `TableShell.vue`。它只替代重复的 `scrollbar-slim overflow-x-auto` 和日志分页/footer padding，不接管表格列定义、数据行、分页状态或任何写入/删除动作。

Monitor 和 PublicUptime 的服务状态卡已统一到 `ServiceStatusCard.vue`。它只展示服务名称、状态、可用率、请求/成功数量和心跳条；`useUptimeStatus` 继续负责轮询、状态计算、tooltip 文案和接口错误处理，页面继续负责标题、打开公开监控页按钮和空态。

后续抽到 `nanocat-ui` 前，先继续在本项目内收敛并保持可构建；确认 API、样式 token 和插槽形状稳定后再发包。

## CodeGraph 工作流

每次做结构改动后同步索引：

```powershell
codegraph sync D:\chatgpt2api
codegraph status D:\chatgpt2api
```

常用查询：

```powershell
codegraph query "accountsApi" -p D:\chatgpt2api -l 20
codegraph query "GET /api/model-catalog" -p D:\chatgpt2api -l 20
codegraph query "get_logs" -p D:\chatgpt2api -l 20
codegraph query "get_images" -p D:\chatgpt2api -l 20
codegraph query "preferenceKeys" -p D:\chatgpt2api -l 20
codegraph impact "get_available_access_token" -p D:\chatgpt2api
```

注意：CodeGraph 对 Vue template 的事件绑定识别不完整，影响面分析要配合 `rg`。

## 2026-06-08 Follow-up UI Contracts

- `ListPagination.vue` is the shared paginator for Accounts, Logs, and Gallery. Page size menus default to downward placement; page components provide `page`, `pageSize`, `totalCount`, options, and refresh behavior.
- `OperationProgressModal.vue` is shared by Logs/Gallery one-shot delete/download flows. It intentionally does not expose stop/cancel for those flows unless the backend gains job/progress/cancel endpoints.
- `Logs.vue` keeps two separate surfaces: call logs are a paginated business table; runtime logs are a read-only terminal panel backed by `/api/runtime-logs`.
- `DetailImagePreview.vue` only renders thumbnails inside the Logs detail drawer. Clicking a thumbnail opens the shared `GalleryLightbox.vue` preview shell; `Logs.vue` owns the selected preview state, URL mapping, download, and copy-link handlers. Logs may show download/copy, but should not show tag editing until log images have a persisted Gallery record. Do not add a second page-local large-image modal for Logs.
- Settings external account source add/edit forms use `ModalShell + ModalHeader + ModalFooter`. Test buttons for CPA/Sub2API remain page-local and are treated as R3 external actions.

## 2026-06-10 Gallery Image Validity Contract

- `services/image_storage_service.py` treats `data/images/**` as real image storage, not arbitrary binary storage. `save()` validates image bytes with Pillow before writing local/WebDAV files; invalid payloads raise `InvalidImageDataError`.
- `services/protocol/conversation.py` converts invalid upstream image payloads into `ImageGenerationError(code="invalid_image_payload", stage="receiving_image")`, so callers see an image-chain failure instead of a fake gallery URL.
- `list_items()` only returns valid local images. If an indexed local file is not a decodable image, the entry is pruned from `data/image_index.json`; WebDAV-backed entries may still fall back to remote bytes when local cache is bad.
- Protocol/unit tests must not write fake bytes such as `b"generated image"` through the real gallery storage path. Use a valid tiny PNG fixture or mock `image_storage_service.save()` when the test is about protocol behavior rather than storage behavior.

## Read-only smoke 边界

2026-06-08 的全路由 smoke 使用临时后端命令：

```powershell
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --lifespan off --no-access-log
```

这样可以让前端读取真实 API，同时不启动 lifespan 中的图片清理、备份调度和账号 watcher。只读 smoke 只允许访问列表、看板、设置读取、日志读取、图片读取和文档页；导入、刷新、重登、代理测试、保存设置、删除、清理、压缩、导出等动作继续按 `docs/frontend-interface-action-map.md` 的 R2-R4 风险等级走手动确认。

## Image latency diagnosis

2026-06-08 只读检查结论：

- 近期图片请求成功耗时约 165s、335s、459s、528s，失败耗时约 260s 到 377s；文本请求多在 4.6s 到 27s。
- 失败日志出现 `curl: (56) Connection closed abruptly`、`response.failed/server_error`、`No image result found in response`、`image_poll_hit_no_settle` 和 `message_preview: {"skipped_mainline":true}`。
- 同一账号既能成功出图，也能失败，因此不是简单的账号额度空或前端页面渲染慢。
- 当前优先怀疑上游图像生成/SSE 等待、文件资产 settle 或代理网络链路不稳定。继续验证需要指定测试账号、测试代理组和测试图像任务，按 R3 手动 smoke 执行。

## 下一步对齐顺序

1. 把重复的下拉、分页、统计卡片继续收敛到项目内 UI 组件；发包到 `nanocat-ui` 前先保持本项目可构建。
2. 手动 smoke 前只做 R0/R1；R2-R4 动作等用户指定测试对象。
