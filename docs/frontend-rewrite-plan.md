# 新前端重写计划

## 目标

使用本地 `D:\gemini2api\frontend` Vue 前端作为交互参考，重写 API 适配层和页面字段，服务 chatgpt2api 的账号池、日志、画廊、设置管理。功能语义优先参考当前项目 `web/src`，分页、弹窗、列表密度和操作方式参考 `D:\gemini2api\frontend`。

## 第一阶段：准备

产物：

- 文档完成：
  - `development-principles.md`
  - `backend-map.md`
  - `image-pipeline.md`
  - `api-contract.md`
  - `frontend-adapter-map.md`
  - `frontend-page-spec.md`
  - `backend-frontend-gap.md`
- 确认前端参考目录：
  - `D:\gemini2api\frontend`

验收：

- 明确哪些页面保留、哪些字段删除、哪些接口改接。
- 不修改后端核心图片链路。
- 明确哪些字段当前不存在，只能作为后端补强项。

## 第二阶段：前端骨架迁移

任务：

- 已把 Vue 前端放到 `web-vue/` 作为迁移目录，确认 build 和接口适配后再替换正式 `web`。
- 保留：
  - AppShell
  - Router
  - Pinia auth store
  - Toast/Confirm composables
  - ChartCard/StatCard 视觉结构
  - Gallery/Logs/Accounts/Dashboard 页面框架
- 删除或隐藏 Gemini 专有：
  - lane
  - snlm0e
  - cookie resolve
  - pro/thinking/fast 模型配额
  - public display
  - password login

验收：

- `web-vue` 的 `npm run build` 通过。
- 登录页、Shell、Dashboard 能打开。

## 第三阶段：API 适配

任务：

- 重写 `src/api/client.ts`
  - 使用 Bearer key。
  - 错误提取兼容 `detail.error` 和 OpenAI error。
- 重写 `src/types/api.ts`
  - 定义 chatgpt2api 的 Account、ImageTask、SystemLog、ManagedImage、Settings。
- 重写：
  - `src/api/auth.ts`
  - `src/api/stats.ts`
  - `src/api/reverseAccounts.ts`，可改名 `accounts.ts`
  - `src/api/logs.ts`
  - `src/api/gallery.ts`
  - `src/api/settings.ts`
  - 新增 `src/api/imageTasks.ts`

验收：

- 每个 API module 有明确类型。
- 页面不直接拼后端字段。
- 所有后端不存在的 gemini 接口都已删除或改接。

当前进度：

- 已完成 `src/api/client.ts`、`src/api/auth.ts`、`src/api/stats.ts`、`src/api/settings.ts`、`src/api/version.ts` 的第一版适配。
- 已完成 Bearer key 登录、本地保存、`/auth/status` 路由守卫、`/api/dashboard` 概览聚合。
- 已完成 `src/api/reverseAccounts.ts`、`src/api/logs.ts`、`src/api/gallery.ts` 的第一版接口适配：账号接 `/api/accounts*`，日志接 `/api/logs` 并在前端聚合诊断字段，画廊接 `/api/images*`。
- 已新增 `src/api/imageTasks.ts` 和 `ImageTasks.vue`，并恢复“画图”入口；普通 user key 登录后只进入画图页。
- 已把账号页文案、字段、按钮从 Gemini 概念重塑成 chatgpt2api 概念：列表展示 token、类型/来源、状态、账号信息、创建时间、图片额度、恢复时间、成功/失败计数；表单提交 access token、type、source_type、status、quota、proxy。
- 已新增 `src/api/accountImports.ts`，适配 OAuth、CPA、Sub2API 账号来源接口；账号页已挂统一导入弹窗。
- 已按 `D:\gemini2api\frontend` 的账号列表方式加入分页，默认每页 50，选项 20/50/100，全选只作用于当前页。
- 当前已进入验收和小范围真测阶段：R0/R1 只读 smoke 已完成；R2 普通编辑保存、R3 外部服务动作和 R4 破坏性动作必须按 `docs/frontend-interface-action-map.md` 的风险等级执行。

## 第四阶段：概览中心

页面：`Dashboard.vue`

数据源：

- 优先接已新增的 `GET /api/dashboard`。
- 临时也可前端聚合：
  - `/health?format=json`
  - `/api/accounts`
  - `/api/logs`
  - `/api/images/storage`

图表：

- 模型请求分布。
- 调用趋势。
- 成功率趋势。
- 平均响应时间。
- 模型调用占比。
- 模型使用排行。

验收：

- 图表非空。
- 图表标题和原版语义一致，不出现“图片请求分布（按模型）”。
- 没有账号时有空状态。
- 概览中心不显示“最近失败日志”面板；失败排查统一进入日志管理页。

当前进度：

- 已完成 `/api/dashboard` 后端聚合和前端 Dashboard adapter。
- 已对齐原版 6 张模型图表：模型请求分布、调用趋势、成功率趋势、平均响应时间、模型调用占比、模型使用排行。
- 已把账号统计卡片改为账号总数、正常账号、限流账号、异常账号、禁用账号、剩余图片额度。
- Header 的“接口信息”已展示基础端点、SDK 接口、完整接口、聊天模型和图片模型。
- 已按当前决策移除“最近失败日志”面板，失败排查保留在日志管理页。
- 2026-06-04 已重新 smoke Dashboard：移除“最近失败日志”后六张模型图表标题仍可见，控制台无错误；后续只补真实空数据场景。
- 2026-06-04 P0 收口：剩余额度不再拼接 `数字+∞`，Header 接口信息优先读取 `/v1/models`，失败时回落 settings/catalog；真实账号池模型列表仍待手动 smoke。

## 第五阶段：账号管理

页面：`Accounts.vue`

功能：

- 列表。
- 搜索邮箱、状态、来源。
- 批量刷新、恢复异常账号。
- 批量删除。
- 单账号编辑状态、quota、proxy，并可测试当前代理。
- OAuth 登录入口。
- CPA/Sub2API 导入可以保留成折叠区。

验收：

- 状态颜色明确。
- token 脱敏。
- 刷新/重登进度可见。

当前进度：

- 已完成列表、分页、搜索、批量刷新/恢复异常/启禁/删除、状态/图片额度/代理编辑和测试、token 脱敏展示。
- 已完成统一导入弹窗：OAuth、Access Token、Session JSON、Codex JSON、CPA JSON 文件、远程 CPA、Sub2API。
- 已完成“刷新所有账号信息和图片额度”进度弹窗，前端按 20 个一批提交刷新任务。
- 已按原版账号行操作形态改成“编辑 + 更多”菜单，更多里保留刷新账号信息和图片额度、恢复异常账号、重置状态、启用/禁用、删除。
- 已把账号列表图片额度改成直接显示数值，不再使用 gemini 的悬浮多配额详情。
- 已完成导出：优先使用 `/api/accounts/export` 导出完整 OAuth/Codex 认证 JSON，缺少完整认证材料时回退导出 access token TXT。
- 已把账号编辑弹窗的 `proxy` 原始输入升级为代理模式选择器：目标口径为使用全局代理、强制直连、代理组、自定义代理。保存值分别对应空字符串、`direct`、`group:<id>` 和原始代理 URL；旧 `profile:<id>` 不再作为新编辑入口展示，只保留历史账号兼容解析和原值保留。
- 2026-06-04 已完成非破坏浏览器 smoke：主表字段、分页、当前页全选、批量菜单、导入模式切换、行菜单和编辑代理入口均可打开，控制台无错误；截图在 `artifacts/accounts-smoke-start-20260604.png`、`artifacts/accounts-smoke-menu-edit-20260604.png`、`artifacts/accounts-import-modes-20260604.png`。真实导入、刷新、恢复、导出下载、代理测试请求仍需单独确认。

## 第六阶段：日志中心

页面：`Logs.vue`

功能：

- 调用日志列表。
- 按类型、状态、endpoint、时间、账号邮箱、conversation id 筛选。
- 图片失败详情抽屉。
- 错误 JSON 格式化。
- 支持复制 conversation_id、account_email、error。

验收：

- 图生图失败能看到具体失败文本。
- 上游文本回复类错误能被识别。
- 日志能反查账号和图片任务。

当前进度：

- 已完成日志中心第一版重写，改成面向 chatgpt2api 的调用日志表格，不再沿用 gemini 的复杂会话分组主视图。
- 已支持 type/date/status/endpoint/model/account/conversation_id/关键词服务端筛选，并支持 `limit/offset` 分页。
- 已接入后端返回的 `total`、`has_more`、`facets` 和 `stats`，日志页筛选选项、统计卡片和分页不再依赖前端全量本地过滤。
- 已支持失败、图生图、文生图、文本回复无图快捷筛选。
- 已支持日志详情抽屉，展示 request_text、error、error_code、stage、reason、account_email、conversation_id、上游文本回复、结果图片预览和 raw detail JSON，并支持复制。
- 日志列表会从 `detail.urls` 提取结果图并展示缩略图，详情抽屉显示图片预览网格；坏图降级为“无法预览”。
- 日志列表时间已改为 `started_at -> time -> ended_at` 兜底，避免新旧日志字段不一致导致时间为空。
- 日志表格已重新对齐旧 `web/src` 主视图：时间、类型、令牌名称、调用耗时、状态、图片、简述、查看详情、删除；长 request_text/error 不再直接显示在列表。
- 已补当前页勾选、全选、取消选择和“删除所选”确认弹窗，批量删除走 `/api/logs/delete`。
- 普通图片异常分支也会把 diagnostics/status_code 写进日志，避免非 `ImageGenerationError` 的图片失败丢失结构化详情。

## 2026-06-04 全面检查记录

当前第一版控制台骨架已接近可用，但还没有完成真实环境等价验收：

> 2026-06-04 更新：用户反馈的概览、账号、设置、代理、日志、图片管理问题已经单独整理到
> `docs/control-panel-issue-audit.md`。后续继续改代码前，以该文档的“已做 / 半做 / 未做 / 下一步实施顺序”为准；
> 本计划里的“当前进度”只表示骨架或接口已接入，不等于功能最终完成。

- 日志管理：已完成服务端筛选、分页、详情、图片预览、时间兜底、旧版主表字段、单条删除和本页勾选/删除所选交互。
- 概览中心：已接 6 张模型图表、账号统计卡和 Header 模型列表；“最近失败日志”面板已按当前决策移除。2026-06-04 已重新 smoke 移除面板后的布局，后续补真实空数据场景。
- 账号管理：已接分页、批量刷新、恢复异常、统一导入弹窗、真实导出和代理选择/测试；非破坏浏览器流程已 smoke 并留存截图，仍要用真实 OAuth/CPA/Sub2API 配置逐个 smoke 导入与操作流程。
- 设置页：已能保存主要配置，并补齐图片存储测试/同步、备份测试/立即备份/历史删除、CPA 连接管理、Sub2API 连接管理和分组读取；仍要做真实 WebDAV、R2、CPA、Sub2API smoke。
- 代理管理：已接全局代理和代理组；仍要做真实代理测试、账号引用 `group:<id>` 的端到端验证。
- 图片画廊：已接搜索、筛选、分页、预览、下载、删除、标签和存储维护；仍要 smoke WebDAV-only 文件、批量 zip 和清理策略。
- 图片任务/本地画图：已恢复入口；必须走 `/api/image-tasks/*`，不要让浏览器长请求直接卡住。
- 运行日志：当前 `/api/logs` 是业务调用日志；真正服务运行日志已新增 `/api/runtime-logs` 只读接口，内存 logger 可直接展示，Docker stdout/stderr 需要部署侧重定向或挂载日志文件。
- 注册机：第一版不接，后续从 `D:\codexzz\webfree_server` 单独任务化。
- 代码清理：已删除未引用的旧日志 composable、脚手架残留 `stores/index.ts`/`lib/utils.ts`，移除未使用依赖，并把 401 拦截器改成入口注册处理器；`npm run build` 已通过且无 Vite 动态/静态混用提示。
- 文档教程：已从 gemini2api 销售/教程内容改为 chatgpt2api 接口说明、运维边界和风险等级，不再展示 Google Cookie、Banana 2 或 nano-banana 示例。

下一步不再是补页面骨架，而是按风险顺序验收：

1. R2 小范围写入 smoke：需要明确测试账号、测试代理分组、测试图片或可回滚设置项。
2. R3 外部副作用 smoke：OAuth、CPA、Sub2API、WebDAV、R2、代理测试和批量账号动作，需要真实配置和当轮确认。
3. R4 破坏性 smoke：删除账号、日志、图片、备份和图库清理，只能在明确测试数据上做。
4. 不依赖真实对象的代码级工作：继续做 docs 一致性、构建、接口映射、旧文件清理和空数据/异常数据 UI 检查。

## 第七阶段：图片任务，暂缓

新增页面：`ImageTasks.vue`

当前决策：显示画图入口，文件和 API adapter 走异步图片任务化工作流。普通 user key 只进入画图页。

功能：

- 创建文生图任务。
- 创建图生图任务。
- 任务队列。
- 任务详情。
- 失败后 resume-poll。
- 结果图片预览。

验收：

- 浏览器不被长请求卡住。
- 任务失败不影响继续提交。
- 有 conversation_id 的失败任务可继续轮询。
- 没有诊断字段时页面也能正常显示兜底信息。

## 第八阶段：图片画廊

页面：`Gallery.vue`

功能：

- 日期筛选。
- 标签筛选。
- 图片预览。
- 下载。
- 删除。
- 批量删除。
- 存储统计。
- 压缩和清理入口。

验收：

- 图片 URL 和缩略图正常。
- 删除前确认。
- 批量操作后刷新列表。

## 第九阶段：设置中心

页面：`Settings.vue`

重点设置：

- 代理。
- 图片超时。
- 图片账号并发。
- 图片并行生成。
- 失败重试。
- 自动移除异常/限流账号。
- 图片存储。
- 备份。
- 用户 key。

验收：

- 保存后能显示新配置。
- 敏感字段不明文回显，或有明确脱敏策略。

当前进度：

- 已去掉 Gemini/Nanobanana/pro/music/video 残留设置。
- 已改成 chatgpt2api 真实配置分组：基础连接、图片链路、账号和并发、缓存、提示词和审核、图片存储、备份。
- `src/api/settings.ts` 会把 `proxy`、`base_url`、`image_retention_days` 同步到旧版 `basic.*` 字段，避免老后端读取路径不一致。
- 已补图片存储测试/同步按钮，调用 `/api/image-storage/test` 和 `/api/image-storage/sync`。
- 已补备份测试、立即备份、刷新历史和删除历史备份，调用 `/api/backup/test`、`/api/backups*`。
- 已补 CPA/Sub2API 连接配置入口；账号管理页远程导入使用这里保存的连接。
- 图片存储测试/同步和备份测试/立即备份只使用已保存配置；表单存在未保存改动时先提示保存，不做隐式保存。
- 2026-06-04 已完成非破坏浏览器 smoke：设置页各配置分组、图片存储、备份、CPA/Sub2API 连接管理均可加载，控制台无错误；真实 WebDAV/R2/外部账号源动作仍待配置后执行。
- 2026-06-04 按用户反馈重新收口设置页：移除顶部空卡片，主视图保留常用设置、账号策略、提示词/审核、图片存储；图片链路、并发、缓存、备份和外部账号源默认折叠；switch 行改为低噪声样式。
- 设置页当前只是回到更简洁的后台配置面板方向，仍未抽成统一设置组件，也未完成移动端/窄屏视觉 smoke。

## 第九阶段补充：代理管理

页面：`Proxy.vue`

功能：

- 全局代理查看、保存、测试。
- 旧代理 profile 列表、搜索、分页。
- 新建、编辑、启用/停用、删除旧代理 profile。
- 多节点代理组列表、节点管理、启用/停用、测试和删除。
- 测试分组代理。
- 复制 `group:<id>` 账号引用。

后端：

- 已新增 `proxy_profiles` 配置归一化，保留旧单 URL profile。
- 已新增 `/api/proxy/profiles*` 和 `/api/proxy/groups*`。
- 请求代理解析前台目标支持 `direct` 和 `group:<id>`。

账号编辑：

- 账号编辑弹窗已接入“全局/直连/旧代理 profile/多节点代理组/自定义代理”选择器。
- 选择代理组时写入 `group:<id>`，请求时由后端代理解析器按账号代理优先级处理。
- 2026-06-04 已完成代理页非破坏 smoke：主视图、全局代理、分组统计、空状态、新建代理分组弹窗均可打开，控制台无错误；截图在 `artifacts/proxy-smoke-main-20260604.png` 和 `artifacts/proxy-smoke-create-modal-20260604.png`。
- 已在 `test/test_system_api.py` 补代理分组接口测试，覆盖创建/列表/删除和 profile 引用解析到代理测试函数。

## 第十阶段：注册机，暂缓

注册机使用：

```text
D:\codexzz\webfree_server
```

第一版不接入主前端。后续可作为任务模块：

- 注册任务。
- 刷新任务。
- 检测任务。
- 任务日志。
- 产物导入账号池。

原因：

- 注册涉及邮箱凭据、网络请求、验证码、脚本运行。
- 和主控制台稳定性风险不同。
- 应当独立任务化，避免误点。

## 当前补充记录：图片画廊

时间：2026-06-03

- `web-vue/src/views/Gallery.vue` 已从基础媒体瀑布流改成 chatgpt2api 图片画廊工作台。
- 已接入搜索、日期筛选、标签筛选、分页、当前页全选、单张/批量删除、批量 zip 下载、复制 URL、标签编辑、过期清理、存储统计、压缩图片、按目标剩余空间预估/执行清理。
- `services/image_service.py` 和 `/api/images` 已补服务端分页、搜索、媒体类型、标签筛选和 `total/counts/total_size` 元数据；`web-vue/src/api/gallery.ts` 优先使用服务端分页结果，旧后端缺少字段时才兜底本地分页。
- `web-vue/src/api/gallery.ts` 已补齐 `/api/images/tags`、`/api/images/storage`、`/api/images/storage/compress`、`/api/images/storage/cleanup-to-target` 适配。
- `web-vue/vite.config.ts` 已补 `/images` 和 `/image-thumbnails` 本地开发代理，避免 5173 预览时缩略图请求不到后端。
- 后端 `services/image_service.py` 已清理重复的 `download_images_zip` 定义；WebDAV-only 原图响应、缩略图生成和 zip 都会通过 `image_storage_service.get_bytes` 兜底读取远端内容，并已有系统测试覆盖。
- 画廊“过期/清理”口径已统一为 `image_retention_days` 保留天数，跟设置页和后端 `config.cleanup_old_images()` 一致；`basic.image_expire_hours` 只保留为旧字段兼容。
## 2026-06-05 Model Catalog Alignment

- Control panel supported-model display now uses `GET /api/model-catalog`.
- Header interface info and Docs share `web-vue/src/composables/useModelCatalog.ts`.
- `/v1/models` is retained as an OpenAI-compatible endpoint and frontend fallback, not as the primary management catalog.
