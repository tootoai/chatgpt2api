# 前端重写状态板

更新时间：2026-06-09

## 当前方案

新控制台以 `D:\gemini2api\frontend` 的 Vue 结构、组件密度和交互方式为参考，但功能语义、字段和接口以 chatgpt2api 为准。也就是说：

- 2026-06-09 密钥收口：Header“接口信息”的密钥展示改为当前浏览器保存的 Bearer key，不再读取 `settings.basic.api_key`；新 Vue 设置页补齐“用户密钥管理”，对接 `/api/auth/users`，支持普通用户 key 的列表、创建、启用/禁用、编辑和删除。普通用户 key 登录后只进入图像创作页，管理员 `auth-key` 仍来自部署配置。
- 外观和交互：参考 gemini2api 的 Vue 控制台。
- 数据和动作：优先对齐当前项目 `web/src` 和现有后端。
- 新前端落点：`web-vue/`，稳定后再考虑替换正式 `web/`。
- 画图入口已恢复，但只走 `/api/image-tasks/*` 异步任务，避免浏览器长请求卡住控制台。
- 已新增 `docs/frontend-interface-action-map.md` 作为前端接口与动作风险地图；后续 smoke 和 UI 补全按 R0-R4 风险等级执行。
- 2026-06-04 已完成 R0/R1 全页面只读 smoke，记录见 `docs/frontend-r0r1-smoke-20260604.md`。
- 2026-06-04 二次只读巡检已覆盖 Dashboard、Accounts、Logs、Gallery、Proxy、Settings、Docs；页面控制台 error 为 0。运行日志只读视图已补入日志管理和 smoke 记录。
- 2026-06-04 已新增 `docs/frontend-r2-r4-smoke-plan-20260604.md`，并在 Docs 页“风险说明”里展示当前验收状态和 R2 测试对象要求。
- 2026-06-04 已完成 R2/R3/R4 动作保护审计：OAuth 登录开始/完成、账号代理测试、远程 CPA 文件列表、Sub2API 账号列表、远程 CPA/Sub2API 导入、账号导出、单账号刷新、账号启用/禁用、全局代理保存、全局代理测试、代理组测试、代理对象启停、系统设置总保存、图片保留天数、清理预估、图片存储测试、图片存储同步、备份测试、立即备份和 Sub2API 分组读取，都已在真实请求前加入确认弹窗；删除/清空/压缩/执行清理继续保留原有确认。
- 2026-06-04 前端构建已通过；浏览器只读验证覆盖 Accounts、Proxy、Gallery、Settings 四个改动页，控制台无错误。已实测 Accounts 导出全部、OAuth 生成 URL、Gallery 保存保留天数、Settings 保存系统设置、Settings 同步本地图片、Settings 测试 WebDAV、Settings 测试备份连接、Proxy 保存全局代理会先弹确认并可取消；OAuth 刷新后验证为取消即不生成授权 URL，未执行账号导入/真实写入/外部存储或代理测试。
- 2026-06-04 已对齐 R2 文档口径：普通编辑弹窗保存，例如账号编辑、代理组编辑、图片标签编辑、CPA/Sub2API 连接编辑，点击保存即视为确认；批量、状态切换、导入、导出、外部测试、同步和删除仍按风险等级加确认。CodeGraph 已检查图库标签保存、批量下载、账号批量刷新和批量菜单入口，影响面均限制在预期页面内。
- 2026-06-04 浏览器只读确认主菜单不包含图片任务/本地画图入口，当前 Accounts 页面控制台错误为 0。此记录已被 2026-06-08 的“画图入口恢复”决策替代。
- 2026-06-04 已完成 `web-vue/src/api` 写入口静态审计：`POST`、`DELETE` 和 `apiClient.request({ method: 'DELETE' })` 均已映射到 `docs/frontend-interface-action-map.md`；当时图片任务写入口仍只保留代码文件，未开放主菜单和路由入口。此记录已被 2026-06-08 的“画图入口恢复”决策替代。
- 2026-06-08 已恢复“画图”主导航入口，并把登录态从只保存 `isLoggedIn` 扩展为保存 `/auth/status` 返回的 `role/name/subject_id`；`admin` 进入完整控制台，`user` 登录或访问管理页时重定向到画图页。后端 `/v1/chat/completions`、`/v1/responses`、`/v1/messages`、`/v1/search`、PPT/PSD/可编辑文件任务改为要求 `admin`，普通 user key 只保留图片生成/图片任务能力。
- 2026-06-04 删除未引用的旧日志 composable `web-vue/src/views/logsPage/useLogsPage.ts`，避免旧清理/分组逻辑干扰当前 `Logs.vue` 审计；重新同步 CodeGraph 并通过 `npm run build`。
- 2026-06-04 删除未引用的脚手架残留 `web-vue/src/stores/index.ts` 和 `web-vue/src/lib/utils.ts`，并移除 `class-variance-authority`、`clsx`、`tailwind-merge` 三个未使用依赖；重新通过 `npm run build`。
- 2026-06-04 完成第二轮风险动作代码审计：Accounts、Proxy、Settings、Gallery、Logs 的导入、导出、刷新、恢复、外部连接测试、同步、备份、删除、清理等真实请求均在请求前确认；账号编辑、代理组编辑、图库标签编辑、CPA/Sub2API 连接编辑仍按 R2 规则作为普通表单保存，不额外叠加二次确认。
- 2026-06-04 将 API 401 拦截器改为入口注册的未授权处理器，避免 `api/client.ts` 动态导入 `auth store/router`；构建通过且不再出现 Vite 动态/静态混用提示。
- 2026-06-04 将 `Docs.vue` 从 gemini2api 销售/教程页改为 chatgpt2api 文档中心，展示接口示例、运维边界和风险等级；浏览器复核无旧 Gemini/nano-banana 展示文案，控制台错误为 0。
- 2026-06-04 补齐 Logs、Gallery、Settings 的加载失败静态提示：GET 失败时不再只依赖 toast，而会在空态/设置占位区显示失败原因和重试入口；Docs、Logs、Gallery、Settings 浏览器只读复核均无控制台错误。
- 2026-06-04 手测前收口检查：当时主导航和路由仍不包含图片任务/本地画图入口；概览中心只保留账号卡片、Header 接口信息和 6 张模型图表。入口部分已被 2026-06-08 的“画图入口恢复”决策替代；Accounts、Proxy、Settings、Gallery、Logs 的真实写入、删除和外部测试入口均已确认有显式按钮或确认弹窗保护。`npm run build` 通过，`python -m unittest test.test_system_api test.test_log_service` 17 项通过，`codegraph status D:\chatgpt2api` 显示索引已最新。真实 R2/R3/R4 smoke 按当前决定暂缓，等手动测试或指定测试对象后再执行。
- 2026-06-04 Docker 打包入口已切换到 `web-vue/`：镜像构建阶段使用 `npm ci && npm run build` 生成 `web-vue/dist`，最终复制到后端 `web_dist`。`.dockerignore` 已排除 `web-vue/node_modules`、`web-vue/dist`、CodeGraph 数据库、截图产物和本地日志，避免打包上下文混入本地文件。
- 2026-06-04 账号存储默认切到本地 SQLite：`data/accounts.json` 和旧 `data/accounts.db*` 已按要求清空，本地从空库 `data/accounts.db` 重新开始。常见账号写入已改为单账号/批量增量写库；1 万账号本地/单容器优先用 SQLite，多容器生产建议 PostgreSQL。
- 2026-06-04 数据存储边界已确认：当前 SQLite 只负责账号和 auth key；配置、远程账号源、日志、图片索引和标签仍保持现有文件/JSONL 形态，等日志页或图库在真实数据下卡顿时再迁移日志/图片元数据。
- 2026-06-04 已收口一轮 UI 细节：账号页默认 20 条并记住页大小，顶部操作改为导入/添加、批量操作、导出三个菜单，Token 脱敏显示并支持点击复制完整值，但不在悬浮或 title 中展示完整内容；日志页调用日志默认 20、运行日志默认 500，并记住选择；设置页去掉临时统计和 legacy proxy 提示；代理编辑弹窗保存后关闭，且确认框层级不再被编辑弹窗压住。
- 2026-06-04 二次 UI 统一：侧边栏图标改为圆形边框；下拉菜单开始统一为 8px 圆角并互斥打开；账号页顶部批量菜单补齐选中账号操作；账号批量刷新、恢复、重置、启用、禁用、删除均复用同一进度弹窗，并支持停止后续批次。
- 2026-06-04 再次修正侧边栏选中态：使用路由 name/path 判断当前菜单，避免子路由下 `router-link-active` 已存在但自定义 class 仍按未选中渲染。设置页 switch-row 试验已按用户反馈回退，不再作为已完成统一项。
- 2026-06-04 当前收口顺序调整：先同步文档，再收口账号页菜单组件。账号组绑定、导入/添加、批量操作、导出、底部批量栏和行内更多应统一走本项目 `FloatingActionMenu`；账号组绑定菜单不显示勾选，菜单宽度按最长选项自适应且至少不小于触发按钮，菜单面板/菜单项/分割线由组件内部统一渲染；菜单分组统一用 `actionMenuGroups()` 生成，避免各处手写 `dividerBefore`。
- 2026-06-04 菜单冗余样式复查：账号页顶部账号组绑定、导入/添加、批量操作、导出四个浮层入口共用同一个 `FloatingActionMenu` 调用方式，只传统一 `trigger-class`，不再在页面层硬编码菜单宽度；导出也按 `actionMenuGroups()` 生成分组分割线；`FloatingActionMenu` 不再保留 `button-class/content-class` 旧别名，避免同一个组件出现两套写法。
- 2026-06-04 账号页顶部工具栏改为两行工作流：第一行只放搜索、状态/账号组筛选和结果汇总/视图切换，第二行连续放账号组绑定、刷新、导入/添加、批量操作和导出，避免宽屏下左右控件割裂和大面积空白。
- 2026-06-05 下拉菜单定位规则已固定：`FloatingActionMenu` 默认向下展开，只有下方空间不足且上方空间更合适时才向上翻转；过高菜单改为面板内部滚动，已覆盖选择账号组、导出和行内“更多”。
- 2026-06-05 账号页补齐“账号组管理”入口：筛选下拉只负责筛选，账号组创建/编辑/启用/停用/删除和绑定默认代理组统一放到独立弹窗；删除账号组只会把原账号清为未分组，不删除账号本身。
- 2026-06-05 账号页工具栏层级重新收口：第一行保持搜索、状态/账号组筛选和选择汇总；第二行拆为账号组绑定工作流、账号导入/批量/导出主操作、右侧低优先级刷新列表。账号组筛选和账号组绑定入口保持语义分离，避免把“刷新列表”混在主操作组里。
- 2026-06-05 代理页完成术语收口和非破坏 smoke：主视图以前台“全局代理 + 代理组”为准；设置页和 Docs 页同步去掉“代理分组”旧称。
- 2026-06-05 本轮前端统一收口：账号编辑代理区改为单一“当前代理”摘要；设置页去掉顶部临时看板和长说明；代理页去掉看板式统计卡并明确全局代理、代理组两层；日志页自动刷新只作用于运行日志；图片管理顶部统计和筛选区做第一轮减负。
- 2026-06-05 本轮页面层级继续收口：设置页恢复到通用设置分组布局；代理页移除旧单代理展示，前台方案以代理组为主；日志页统计改成紧凑指标卡；图片管理曾尝试把维护工具独立并折叠，随后已按反馈回收到顶部单框常驻展示。`npm run build` 通过，浏览器只读检查 Settings、Proxy、Logs、Gallery 控制台 error 为 0。
- 2026-06-05 日志页继续减负：标题、统计小卡片、视图切换、刷新/导出/清空、搜索、日期、快捷筛选和高级筛选都合并到同一个控制面板；“只看失败/图生图/文生图/文本回复无图”和运行日志级别/来源改为 `FloatingActionMenu` 下拉，表格成为第二个主块。更多条件已从原生展开块改为可连续选择的下拉面板，类型、状态、模型、账号可以同时生效。`npm run build` 通过，浏览器检查 `/logs` 控制台 error 为 0，截图在 `artifacts/logs-compact-filter-20260605.png`。
- 2026-06-05 视觉口径微调：日志和图片管理不走纯扁平 chip，也不把指标塞进标题左侧；统计恢复为标题/按钮下方的一行横向卡片，窄屏再换行，保留卡片质感但不恢复分散的大看板。
- 2026-06-05 图片管理按最新反馈改回顶部单框结构：标题/统计、搜索/标签/日期放在同一个控制面板内；移除“筛选”标题、媒体类型切换、重置筛选入口和维护工具折叠态。图片列表仍作为第二个主要内容块，每页数量留在列表工具条；图片卡片文件信息区保持稳定高度，标签只露出一行，减少网格高度跳动。后续又按最新决策移除了主界面的保留策略、存储维护和存储进度条。
- 2026-06-08 画图页按原版 `web/src/app/image` 的对话工作台重新收口：路由保持普通控制台页面，外层 header 和 sidebar 不隐藏，只把中间内容区换成画图工作台；画图页内部仍保留自己的历史侧栏。右侧为用户 prompt 靠右、结果靠左的消息流，底部为原版风格 composer；成功结果按图片附件式紧凑排版，操作只保留“加入编辑/下载/回填提示词”这类画图流动作，失败和运行态只作为对话结果占位，不再做管理页任务卡片。后续改画图页必须先对照 `web/src/app/image/page.tsx`、`image-composer.tsx`、`image-results.tsx`、`image-sidebar.tsx`，不要重新发明图片预览、结果流或任务面板。
- 2026-06-09 画图模型和额度口径收紧：图片模型只显示配置项或从“可用图片账号”能力推导出的模型，禁用、限流、异常和已无已知额度的账号不再贡献 Codex/Plus/Team/Pro 派生模型；完全无配置/账号依据时只兜底 `gpt-image-2`。额度只在画图 composer footer 展示，不再挂到全局侧边栏；未读取到额度时显示“额度读取失败”，真实 0 时显示“剩余 0 张”。成功出图后的本地额度扣减仍由后端 `mark_image_result(success=True)` 统一处理，前端只负责刷新显示。
- 2026-06-09 修复图像创作 footer 假 0：旧后端进程没有 `/api/image-tasks/quota` 时会落到 SPA HTML fallback，前端过去会把非 JSON 响应归一化成 0。现在 `/api/...` 缺路由返回 JSON 404，前端 quota 归一化要求对象响应，失败时显示“额度读取失败”；`GET /api/image-tasks` 同步返回 `quota_summary`，footer 可从任务列表响应先拿到真实额度，再用独立 quota 接口刷新。
- 2026-06-09 画图尺寸选择继续收口：前端把 API 的 `size` 拆成“比例 + 分辨率”两段选择，再映射回 `auto`、`1024x1024`、`1024x1536`、`1536x1024` 等真实提交值。普通 `gpt-image-2` 默认只显示自动和 1K 规格；`codex-gpt-image-2` 及 plus/team/pro 前缀 Codex 模型才显示 2K/4K。选中态不加粗、不改变按钮尺寸；等待/失败占位使用固定比例框，成功结果按真实图片比例展示，避免最终图片被等待框尺寸绑死。
- 2026-06-09 图像创作多参考图口径确认：前端上传框允许多选、粘贴和拖入多张图；提交图生图时会把多个上传文件都作为 `image` 表单字段发送，多个远程 URL 会写入 `images` JSON 字段。后端 `/api/image-tasks/edits` 经 `api/image_inputs.py` 读取为多张图片，再由 `services/protocol/openai_v1_image_edit.py` 编码进 `ConversationRequest.images`。如果多图失败，排查顺序是 URL 下载/50MB 限制、上游模型是否接受多参考图、模型尺寸/质量参数，而不是先假设前端不支持多图。这里的“多图”只指多张参考图输入；一次请求输出多张结果图已在 2026-06-10 通过任务 `n=1..4` 支持。

## 已可用

### 登录和壳

- Bearer key 登录已接 `POST /auth/login`。
- 登录状态已接 `GET /auth/status`。
- Shell、路由守卫、侧边栏、Toast、Confirm 已可用。
- 文档教程页已改为 chatgpt2api 语义，不再展示 gemini2api 销售、Cookie 或 Banana 2 教程内容。

### 概览中心

- 数据源已接 `GET /api/dashboard`。
- 卡片已按 chatgpt2api 改为：账号总数、正常账号、限流账号、异常账号、禁用账号、剩余图片额度。
- 图表已对齐原版模型维度：模型请求分布、调用趋势、成功率趋势、平均响应时间、模型调用占比、模型使用排行。
- Header 的“接口信息”已展示基础端点、SDK 接口、完整接口、聊天模型和图片模型。
- 已按当前决策移除“最近失败日志”面板，概览中心只保留账号卡片、接口信息和模型图表。
- 2026-06-04 已重新 smoke Dashboard：移除“最近失败日志”后六张模型图表标题仍可见，控制台无错误；截图在 `artifacts/dashboard-no-recent-failures-20260604.png`。后续只补真实空数据场景。

### 账号管理

- 列表已改成 chatgpt2api 账号语义：TOKEN、类型/来源、状态、账户信息、创建时间、图片额度、恢复时间、成功/失败、操作。
- 已有分页，默认 20，选项 20/50/100，当前页全选，并记住用户选择的页大小。
- 已有批量进度弹窗，前端按 20 个一批提交；刷新、恢复、重置、启用、禁用、删除都会显示进度，停止按钮会在当前批次完成后停止后续批次。
- “刷新账号信息和额度”的当前后端语义是组合动作：`POST /api/accounts/refresh` 进入 `account_service.refresh_accounts()`，刷新远端账号信息、状态、套餐/额度和恢复时间；如果账号带 `refresh_token` 且 access token 需要刷新，会先刷新 access token。它不是“只刷新 AT”，也不是“只刷新额度”；密码重新登录/恢复异常账号走 `/api/accounts/re-login`。
- 导入弹窗已覆盖：OAuth、Access Token、Session JSON、Codex JSON、CPA JSON 文件、远程 CPA、Sub2API。
- 顶部入口已收为“导入 / 添加”“批量操作”“导出”三个菜单，避免按钮拥挤；三个顶部菜单使用一致的触发按钮宽度和浮层样式。添加账号和导入账号在同一入口下，批量菜单同时包含全局操作和选中账号操作，未选中账号时相关项置灰。
- 账号组管理、绑定分组、刷新列表和三大菜单同属账号页顶部工具栏；下拉入口走 `FloatingActionMenu`，普通动作用同一套 toolbar button class 对齐高度、圆角、padding 和颜色，不要在页面层临时写一套外观。
- 已新增账号组管理弹窗：可创建/编辑账号组，设置稳定 ID、显示名称、启用状态、备注和默认代理组；创建后账号组会出现在筛选、编辑账号和批量绑定入口中。
- Token 列表中脱敏显示，点击复制完整 access token/cookie；悬浮提示只显示“点击复制完整 Token”，不再暴露完整 token。
- 行操作已改成“编辑 + 更多”，更多里放刷新、重置、启用/禁用、删除等操作。
- 账号代理已支持全局代理、强制直连、代理组和自定义代理；账号页不再展示旧 `profile:<id>` 选择入口，已有历史账号会按自定义/历史引用保留原值。
- 账号编辑弹窗里的代理区已减掉重复的“代理模式 / 账号代理”展示；当前代理、刷新代理配置和测试当前代理按模式分层显示。
- 已接恢复异常账号：顶部可恢复全部异常账号，批量菜单和行操作也可触发 `/api/accounts/re-login` 并展示进度。
- 异常、受限、禁用行背景按同一套状态分类显示，启用/禁用切换后不再因为只看 raw `status` 而丢失异常视觉。
- 已接真实导出：优先调用 `/api/accounts/export` 导出完整 OAuth/Codex 认证 JSON；如果账号缺少 refresh_token/id_token，则回退导出 Access Token 文本。
- 编辑账号弹窗已接代理测试：全局代理、自定义代理和代理组分别走对应测试接口；旧 profile 测试入口已随账号页收口移除。
- 2026-06-04 已完成账号页非破坏烟测：主表字段、分页、当前页全选、底部批量菜单、导入弹窗 7 种模式切换、行内“编辑 + 更多”、编辑弹窗代理入口均可用；控制台无错误。截图在 `artifacts/accounts-smoke-start-20260604.png`、`artifacts/accounts-smoke-menu-edit-20260604.png`、`artifacts/accounts-import-modes-20260604.png`。
- 2026-06-04 已补 OAuth 登录开始/完成、账号导出和远程账号来源读取的确认保护；浏览器已验证“OAuth 生成 URL”、“导出全部”和“远程 CPA 加载文件”会先弹确认并可取消，Sub2API 加载按钮在当前环境禁用，待真实配置 smoke。
- 还需要真实账号 smoke：OAuth、CPA、Sub2API、批量刷新、恢复异常、导出下载和代理测试实际请求。

### 日志管理

- 已接 `GET /api/logs` 和 `POST /api/logs/delete`。
- 服务端筛选已支持 type、date、status、endpoint、model、account、conversation_id、search、limit、offset。
- 调用日志默认每页 20，运行日志默认 500，并分别记住用户选择。
- 常驻筛选已收进同一个控制面板：调用日志保留关键词和日期作为主筛选，类型/状态/模型/账号放进“更多条件”下拉面板，图生图、文生图、文本回复无图和只看失败走筛选下拉设置 endpoint/error/status 条件。
- 列表已对齐旧 `web/src` 主视图：时间、类型、令牌名称、调用耗时、状态、图片、简述、操作。
- 长 request/error、诊断字段、上游文本回复、raw JSON 已放到详情抽屉。
- `detail.urls` 已支持图片预览，坏图显示“无法预览”。
- 已补当前页勾选、全选、取消选择和“删除所选”确认弹窗，批量删除走 `/api/logs/delete`。
- 日志加载失败时，空态会显示失败原因，避免只靠 toast 排错。
- 自动刷新只保留在运行日志视图；运行日志的级别/来源也收进筛选下拉，调用日志不再显示自动刷新开关。
- 运行日志已新增只读 `/api/runtime-logs`：内存来源读取项目统一 logger，文件来源会尝试读取常见部署日志路径或 `CHATGPT2API_RUNTIME_LOG_FILE` 指定路径；Docker stdout 仍需部署侧重定向/挂载文件才可完整展示。

### 图片管理

- 已接 `GET /api/images`、删除、下载、标签、存储统计、压缩和清理。
- `/api/images` 已支持服务端分页、搜索、日期、媒体类型、标签筛选和 `total/counts/total_size` 统计；前端只在旧后端缺少分页字段时退回本地分页。
- 已支持分页、搜索、日期、标签、预览、复制 URL、单张/批量删除、批量 zip。
- 图片管理顶部统计已降为当前视图、图库总量、当前占用、磁盘剩余四项，并以一行横向卡片展示；已选择数量只在选择工具条里显示。
- 图片管理顶部控制面板现在合并三段：统计卡片、搜索/标签/日期输入、维护工具；媒体类型切换和重置筛选入口已移除，避免出现“全部/图片”这种重复筛选。
- 主界面已移除维护工具、保留策略、存储维护和存储进度条；图片页只保留筛选、分页、预览、标签、选择、单张动作和批量动作，维护接口保留给后续专项入口。
- 图片网格卡片已补稳定信息区和标签一行截断，减少标签数量造成的卡片高度跳动。
- 画廊加载失败时，空态会显示失败原因；坏图继续显示媒体兜底。
- Vite 已代理 `/images` 和 `/image-thumbnails`。
- 2026-06-04 已完成画廊非破坏 smoke：本地 1021 张图库下页面只渲染 24 张当前页，`/api/images?limit=2&offset=48` 返回 2 条并保留 `total=1021`；控制台无页面错误。浏览器截图接口曾因 CDP 截图超时失败，不影响页面状态检查。
- 2026-06-04 已补 WebDAV-only 代码级回归：本地缺失时原图响应、缩略图生成和批量 zip 都会通过 `image_storage_service.get_bytes` 读取远端内容；`download_images_zip` 重复定义已清理为单一实现。
- 2026-06-04 已统一画廊保留/过期口径：图库页按 `image_retention_days` 天数显示和计算过期，跟设置页和后端自动清理一致；旧字段 `basic.image_expire_hours` 只作为兼容写回。浏览器 smoke 显示 1021 张图库、当前页 24 张、倒计时为“天/小时”格式，截图在 `artifacts/gallery-retention-days-20260604.png`。
- 还需要真实环境 smoke：WebDAV-only 图片、批量 zip、清理策略和坏图降级。

### 代理管理

- 已接全局代理保存和 `/api/proxy/test`。
- 多节点代理组已接 `/api/proxy/groups*`，支持一个代理组多个节点、round-robin 选点、节点测试结果写回。
- UI 语义已改为代理组优先：代理管理页不再展示单代理兼容区，后续前台只维护代理组。
- 账号代理值约定：空值使用全局代理，`direct` 强制直连，`group:<id>` 使用代理组。
- 后端代理解析优先级已接：账号单独代理或 direct > 账号组绑定代理组 > 全局代理 > 直连；真实图像链路仍需用测试账号和测试代理做端到端 smoke。
- 代理组编辑保存成功后会关闭弹窗；弹窗内测试代理时，确认框层级高于编辑弹窗。
- 2026-06-05 已把代理页用户可见语义收为“全局代理 + 代理组”；代理组测全部和测单个节点都已补外部请求确认。
- 2026-06-05 已完成代理页非破坏 smoke：主视图、全局代理、新建代理组弹窗均可打开，控制台无错误。
- 已补系统接口测试覆盖多节点代理组创建/列表/删除、group 节点轮询与测试写回。
- 还需要 smoke：真实代理测试、账号引用 `group:<id>` 后的图片请求链路。

### 设置中心

- 已去掉 Gemini/Nanobanana/音乐/视频等无关配置。
- 已改成 chatgpt2api 真实配置分组：基础连接、图片链路、账号和并发、缓存、提示词和审核、图片存储、备份。
- 设置页整体布局已按用户反馈回退到更接近原来的紧凑表单，不再把 switch-row 试验稿视为完成状态；顶部临时统计和代理长说明已移除，页面回到表单优先。
- 设置页当前采用一个大圆角“配置面板”包裹内部设置分组，避免标题卡和设置块分散。
- 已补图片存储测试/同步、备份测试/立即备份/历史删除、CPA 连接管理、Sub2API 连接管理和 Sub2API 分组读取。
- 图片存储测试/同步、备份测试/立即备份现在不再隐式保存表单；有未保存改动时会提示先保存，避免“点测试实际改配置”。
- 设置加载失败时，页面会显示失败原因和重新加载按钮，不再长时间停在“设置加载中”。
- 2026-06-04 已完成非破坏设置页 smoke：基础连接、图片链路、缓存、提示词和审核、图片存储、备份、CPA/Sub2API 连接管理均可加载，控制台无错误；截图在 `artifacts/settings-smoke-mid-20260604.png` 和 `artifacts/settings-smoke-bottom-20260604.png`。
- 还需要真实环境 smoke：WebDAV、R2 备份、CPA 列文件、Sub2API 读分组/读账号。

## 暂缓

- 画图完整页已恢复为主导航入口；概览中心保留轻量画图面板，后续仍必须走 `/api/image-tasks/*`，不要再让浏览器直接等待长图像请求。画图页样式以原版对话工作台为基准，不按账号/日志/图片管理页的后台表格或卡片样式重写。
- 注册机：第一版不接，后续从 `D:\codexzz\webfree_server` 单独任务化。
- 微软/webfree 注册：第一版先不接，后续作为独立导入/刷新模块接入。账号组基础模型已接入，可用于手动分组和绑定默认代理组；按来源自动归组、组级刷新和注册机联动仍待后续设计。
- 公开日志和公开 uptime：可后续恢复。
- 真正运行日志：已接 `/api/runtime-logs` 只读视图；如要看 Docker stdout/stderr，需要部署侧写入文件并通过 `CHATGPT2API_RUNTIME_LOG_FILE` 挂载。

## 下一步顺序

1. 形成可手测检查点：保留当前前端改写结果，准备提交/打包，后续问题按手动测试反馈逐项修。
2. R2 小范围写入 smoke：用明确测试对象验证保存设置、账号编辑、标签编辑、代理组编辑；普通编辑弹窗点击保存即视为确认，不额外叠加二次确认。
3. R3 外部副作用 smoke：OAuth、CPA、Sub2API、WebDAV、R2、代理测试、批量刷新和恢复异常账号，需要真实配置和明确确认。
4. R4 破坏性 smoke：只在明确测试数据上验证删除账号、删除日志、删除图片、清理图库、删除备份。
5. 后端缺口：运行日志只读链路已接入；画图完整页和概览轻量画图面板都走 `/api/image-tasks/*`。

R2 真测前需要先指定或临时创建这些测试对象，避免误改真实账号池：

- 测试账号：允许编辑 access token、代理、状态、配额并可恢复/删除的账号 ID。
- 测试代理对象：允许新增节点、测试节点、编辑和删除的 `group:<id>` 代理组。
- 测试图片：允许改标签、下载 zip、删除的图片路径或专门测试标签。
- 测试设置项：允许临时修改并回滚的设置字段，例如图片保留天数或无副作用的说明字段。

## 验收命令

前端构建：

```powershell
cd D:\chatgpt2api\web-vue
npm run build
```

后端基础回归：

```powershell
cd D:\chatgpt2api
.\.venv\Scripts\python.exe -m unittest test.test_system_api test.test_log_service
```

浏览器冒烟：

```text
http://127.0.0.1:5173/#/
http://127.0.0.1:5173/#/accounts
http://127.0.0.1:5173/#/logs
http://127.0.0.1:5173/#/gallery
http://127.0.0.1:5173/#/settings
http://127.0.0.1:5173/#/proxy
```

## 2026-06-05 账号列表写入性能诊断

- 结论：当前账号新建/编辑/删除/批量操作的慢感主要不是 SQLite 索引问题。`accounts.access_token` 已有唯一索引，临时库 1 万账号下单行更新约 1ms，20 个账号批量更新约 15ms，20 个账号删除约 3ms。
- 真实瓶颈：旧路径在账号 mutation 后会拼接并返回全量 `items`，1 万账号时响应约 5.57MB，单次 JSON 序列化约 120ms；前端批量启用/禁用/删除/重置以前还会拆成每个账号一个 HTTP 请求，叠加后会明显慢。
- 已改：`/api/accounts/update` 只返回 `item`，不再返回全量账号列表；`DELETE /api/accounts`、删除账号组、批量绑定账号组改为轻量计数/分组响应；服务层 `update_accounts/delete_accounts` 新增 `include_items=False` 快路径。
- 已改：新增 `POST /api/accounts/batch-update`，前端批量启用/禁用/重置按每批 20 个账号走批量请求，批量删除走一次批量删除请求；进度弹窗保留，停止会在当前批次结束后生效。
- 已改：编辑已有账号改走 `/api/accounts/update`，只写本地字段，不再误走新增/导入接口，也不会因为编辑触发外部 `refresh_accounts`。
- 已验证：`python -m compileall api\accounts.py services\account_service.py services\storage\database_storage.py` 通过；`web-vue/npm run build` 通过；账号页浏览器 smoke 加载 1028 个账号且控制台 error 为 0。

## 2026-06-05 Account page performance follow-up

- Implemented server-side account list pagination for the Vue page: `GET /api/accounts?page=1&page_size=20&keyword=&status=all&group_id=all`. The no-param form remains compatible and returns the full list for old callers.
- Account add/import paths now opt out of full-list serialization through `add_accounts(..., include_items=False)` and `add_account_items(..., include_items=False)`. This covers manual add/import, CPA import, Sub2API import, and register import.
- `POST /api/accounts/refresh` with an empty `access_tokens` list is now the intended "refresh all accounts" path for the UI; it resolves all tokens on the backend and returns progress only, not current-page fake progress.
- Added regression coverage in `test/test_accounts_api.py` for paginated list forwarding and lightweight account creation.
- Restarted the local backend and verified the paginated account API now returns `items=20`, `total=1028`, `all_total=1028`, `page=1`, `page_size=20`; browser smoke confirms the account table renders 20 rows with no console errors.
- Account-group payloads now include backend-computed `account_count`. The account-group modal and delete confirmation must use this field instead of inferring counts from the current paginated account page.
- Verification after this follow-up: run `python -m unittest test.test_accounts_api test.test_system_api` and `npm run build` from `web-vue/`.

## 2026-06-05 Read-only smoke

- Scope: build, backend key tests, core read-only API, and main Vue routes. No real account import/refresh, proxy external test, settings save, image tag edit, delete, cleanup, backup, or other write/destructive action was executed.
- Frontend build passed: `web-vue/npm run build`.
- Backend tests passed after a small compatibility fix: `python -m unittest test.test_accounts_api test.test_system_api test.test_log_service test.test_image_service` ran 23 tests OK. The fix keeps `services.image_service.list_images(..., tags="x")` compatible while the public API and frontend continue using `tag`.
- Core read-only APIs returned 200: `/health?format=json`, `/api/dashboard`, `/api/accounts?page=1&page_size=20`, `/api/logs?limit=20&offset=0`, `/api/runtime-logs?limit=20`, `/api/images?limit=24&offset=0`, `/api/images/storage`, `/api/proxy/groups`, `/api/settings`.
- Current local API snapshot: accounts `total=328`, first page `items=20`; call logs `total=2056`; gallery `total=1021`, first page `items=24`, storage about `641 MB`; proxy groups `0`; runtime logs `0`.
- Browser route smoke passed with no new console errors and no horizontal overflow: Dashboard, Accounts, Logs, Gallery, Settings, Proxy, Docs. Gallery stabilized at 1021 images after loading; Settings stabilized after loading the config form.
- Closed risk: supported models no longer depend on `/api/dashboard`. Header interface info and Docs read the dedicated `/api/model-catalog` contract instead.
- Database optimization decision remains unchanged for now: accounts/auth keys use SQLite; logs, settings, proxy groups, account groups, image index/tags remain file-backed. Do not migrate more tables until manual smoke or real data shows a concrete bottleneck.
## 2026-06-05 Model Catalog Contract

- Added a read-only management model endpoint: `GET /api/model-catalog`.
- Header interface info and `Docs.vue` now use `web-vue/src/composables/useModelCatalog.ts` so supported chat/image models share one source of truth.
- Fallback order is `/api/model-catalog`, then `/v1/models`, then local settings/catalog defaults.
- Backend source file: `services/model_catalog_service.py`; route: `api/system.py`.
- Smoke passed after restarting the local backend: `/api/model-catalog` returned JSON with chat/image model lists, Header "接口信息" showed `gpt-5`, `gpt-image-2`, and `codex-gpt-image-2`, and Docs showed the same catalog with no browser console errors. Screenshots: `artifacts/model-catalog-header-20260605.png`, `artifacts/model-catalog-docs-20260605.png`.
- Frontend request boundary rechecked with static search and CodeGraph: page/view components do not call `fetch`, `axios`, or bare `apiClient`; requests stay behind `web-vue/src/api/*.ts`. The `api/index.ts` barrel no longer exports the raw `apiClient`.

## 2026-06-06 Frontend Component Consolidation

- First consolidation slice completed: Logs and Gallery metric cards share `web-vue/src/components/ai/MetricStrip.vue`; Dashboard's top stats were later moved back to the original `nanocat-ui StatCard`.
- `MetricStrip` supports compact/normal density, Iconify icons for gallery stats, plain text metrics for logs, and compact progress/status metrics for account modals.
- Removed page-local statistical card DOM/classes from the current source path; Dashboard/Logs/Gallery no longer need separate `log-stat-*` or `gallery-stat-*` styling for top metrics.
- Verification passed: `npm run build` from `web-vue/`.
- Browser read-only smoke passed on `http://localhost:5173/?cb=...#/`, `#/logs`, and `#/gallery`: metric strips rendered as 6/6/4 cards, no horizontal overflow, old log/gallery stat DOM count was 0, console error count was 0.
- No real account refresh/import/delete, proxy external test, image cleanup/delete, WebDAV/R2 action, settings save, or other write/destructive action was executed in this consolidation slice.
- Continued the same consolidation pass with `web-vue/src/components/ai/FilterToolbar.vue`: Logs and Gallery now share the filter toolbar layout wrapper while keeping page-local search/date/dropdown state unchanged.
- Verification passed after the FilterToolbar slice: `npm run build`; browser read-only smoke on `#/logs` and `#/gallery` showed one `.filter-toolbar` per page, no horizontal overflow, and console error count 0.
- Accounts toolbar outer layout also moved to `FilterToolbar.vue`: search/status/group filters, account-group binding, import/batch/export, and refresh clusters now share the same flex/gap/mobile behavior while keeping their existing `FloatingActionMenu` and account-group business logic.
- Verification passed after the Accounts toolbar slice: `npm run build`; browser read-only smoke on `#/accounts` showed four `.filter-toolbar` clusters, the expected toolbar controls, no horizontal overflow, and console error count 0.
- Added `web-vue/src/components/ai/DateRangeInputs.vue` and replaced the duplicated date-range DOM/CSS in Logs and Gallery. Pages now keep only their own state binding and width CSS variables.
- Verification passed after the DateRangeInputs slice: `npm run build`; browser read-only smoke on `#/logs` and `#/gallery` showed one `.date-range-inputs` component per page, two date inputs per component, no horizontal overflow, and console error count 0.
- Added `web-vue/src/components/ai/PanelHeader.vue` and moved the duplicated Logs/Gallery title + action-row layout into it. Button actions remain page-local.
- Verification passed after the PanelHeader slice: `npm run build`; browser read-only smoke on `#/logs` and `#/gallery` showed one `.panel-header` per page, expected title/action counts, no horizontal overflow, and console error count 0.
- Added `web-vue/src/components/ai/ActionRow.vue` and moved Gallery retention, storage-maintenance, and list batch action rows onto it. The component only controls flex/gap/alignment/mobile stretch; Gallery keeps all save/cleanup/download/delete logic.
- Verification passed after the ActionRow slice: `npm run build`; browser read-only smoke on `#/gallery` showed four `.action-row` instances, two maintenance cards, one content toolbar, no horizontal overflow, and console error count 0.
- Added `web-vue/src/components/ai/SelectionBulkBar.vue` and moved the shared fixed-bottom bulk-selection shell into it. `Gallery.vue` now uses it for selected images, and `AccountBulkBar.vue` composes it for selected accounts while keeping account-specific batch menu logic.
- Verification passed after the SelectionBulkBar slice: `npm run build`; browser read-only smoke on `#/gallery` showed one metric strip, four metric cards, one filter toolbar, one panel header, four action rows, zero old `.gallery-bulk-bar` nodes, no horizontal overflow, and console error count 0. `#/accounts` also loaded with no horizontal overflow and no console errors; the current local page had no selectable account rows, so bulk-bar click smoke was not executed there.
- Added `web-vue/src/components/ai/ModalShell.vue` as the shared modal overlay/panel shell. Proxy group modal and Gallery tag editor modal now use it; page logic still owns the form fields, save buttons, close behavior, and confirmation prompts.
- Verification passed after the ModalShell slice: `npm run build`; browser read-only smoke on `#/proxy` opened and closed “新建代理组” without saving, showed one `.modal-shell` with z-index 120 and no horizontal overflow, then `#/gallery` loaded with zero stray modal nodes, four metric cards, no horizontal overflow, and console error count 0.
- Accounts modal shells were then migrated to the same `ModalShell`: add/edit account, account group management, import/add flow, and refresh-progress modal now share the same overlay, panel radius, width, and z-index contract.
- Verification passed after the Accounts ModalShell slice: `npm run build`; browser read-only smoke on `#/accounts` opened and closed “账号组管理” and the “手动添加账号” modal without saving, showed expected modal titles, no horizontal overflow, and console error count 0. The refresh-progress modal was build-verified only, because opening it requires a real batch refresh/import action.
- `ModalShell` now supports horizontal placement for right-side drawers. Logs detail view was migrated from a page-local `Teleport + fixed inset` drawer to `ModalShell placement=\"end\"`, and Header API information moved from a page-local centered modal to the same shell.
- Verification passed after the Logs/AppShell modal slice: `npm run build`; browser read-only smoke on `#/logs` opened and closed the first available “日志详情” drawer, then opened and closed Header “API 接口”. Both checks had one `.modal-shell` while open, zero after close, no horizontal overflow, and console error count 0.
- Added `web-vue/src/components/ai/PagePanel.vue` as the shared page panel shell. Logs and Gallery now use it for the top control panel and the main list/grid panel; `flush` replaces repeated `!p-0 overflow-hidden` page-local section classes.
- Verification passed after the PagePanel slice: `npm run build`; browser read-only smoke on `#/logs` and `#/gallery` showed two `.page-panel` blocks on each page, one flush panel on each page with zero padding and hidden overflow, no horizontal overflow, and console error count 0.
- Accounts, Proxy, and Settings were migrated to `PagePanel` for their page-level panels as well. This removes remaining page-level bare `section.ui-panel` wrappers from the main control-panel pages while preserving page-specific spacing classes.
- Verification passed after the remaining PagePanel slice: `npm run build`; browser read-only smoke on `#/accounts`, `#/proxy`, and `#/settings` showed expected panel counts, zero legacy `ui-panel` wrappers without `page-panel`, no horizontal overflow, and console error count 0.
- Added `web-vue/src/components/ai/StateBlock.vue` as the shared loading/empty/error block shell. Accounts loading/account-group/CPA-file states, Proxy empty/loading states, and Settings external-source/load-failure states now share the same bordered/dashed/compact state styling.
- Verification passed after the StateBlock slice: `npm run build`; browser read-only smoke on `#/accounts`, `#/proxy`, and `#/settings` showed Proxy and Settings state blocks rendering with the expected solid/dashed/compact styles, Accounts had no active empty block in the current local data state, all three pages had no horizontal overflow, and console error count 0.
- Added `web-vue/src/components/ai/TableShell.vue` as the shared table shell for horizontal scrolling and optional footer padding. Accounts list mode, Logs system/runtime tables, and Proxy group table now use it while keeping columns, rows, empty states, pagination state, and actions page-local.
- Verification passed after the TableShell slice: `npm run build`; browser read-only smoke on `#/accounts`, `#/logs`, and `#/proxy` showed expected table-shell rendering where data tables are present, zero legacy overflow wrappers outside the component, no horizontal overflow, and console error count 0. Proxy had no local proxy groups, so its table shell remained naturally unmounted behind the empty state.
- Proxy page header consolidation completed: `Proxy.vue` now uses `PanelHeader` for both the global proxy panel and proxy-group panel, and `ActionRow` for the global proxy test/clear button row. The proxy save/test/group business logic remains page-local.
- Verification passed after the Proxy header/action-row slice: `npm run build`; browser read-only smoke on `#/proxy` showed two `.panel-header` nodes, one `.action-row`, two `.page-panel` blocks, no horizontal overflow, and console error count 0. No proxy save, external proxy test, group create/edit/delete, or settings write was executed.
- Docs page shell consolidation completed: `Docs.vue` now uses `PagePanel` and `PanelHeader` for the read-only documentation panel while keeping API examples, risk rows, model catalog loading, and tab state unchanged.
- Verification passed after the Docs shell slice: `npm run build`; browser read-only smoke on `#/docs` showed one `.page-panel`, one `.panel-header`, zero legacy `section.ui-panel:not(.page-panel)`, no horizontal overflow, and console error count 0.
- Added `web-vue/src/components/ai/ModalHeader.vue` as the shared modal/drawer title bar. Accounts account edit, account group management, import/add, and progress modals; Logs detail drawer; Proxy group modal; Gallery tag editor modal; and Header API information modal now share the same title/subtitle/action/close layout.
- Verification passed after the ModalHeader slice: `npm run build`; browser read-only route smoke covered `#/`, `#/accounts`, `#/logs`, `#/proxy`, `#/gallery`, `#/settings`, and `#/docs` with no horizontal overflow and console error count 0. Safe modal smoke opened and closed Header “API 接口”, Proxy “新建代理组”, Logs “日志详情”, and Accounts “账号组管理” without saving, testing, deleting, importing, refreshing accounts, or triggering external requests. Gallery tag editor header is build-verified; the current local gallery state did not expose a safe visible tag-edit trigger during this smoke.
- Added `web-vue/src/components/ai/ModalFooter.vue` as the shared modal action footer. Accounts account edit, Proxy group edit, Gallery tag editor, and Header API information modal now share the same footer border/padding/gap/alignment contract while keeping every save/clear/close action page-local.
- Verification passed after the ModalFooter slice: `npm run build`; browser read-only smoke opened and closed Accounts “手动添加账号”, Proxy “新建代理组”, and Header “API 接口” without saving, testing, deleting, importing, refreshing accounts, or triggering external requests. Each opened modal showed one `.modal-footer`, no horizontal overflow, and console error count 0. Gallery tag editor footer is build-verified; the current local gallery state had no image card/tag-edit trigger available.
- Added `web-vue/src/components/ai/FormSection.vue` as the shared form section shell. Accounts account edit modal now uses it for 基础信息、Access Token and 调度属性, replacing repeated `rounded-xl border bg-card p-3` wrappers while keeping every field binding, validation, proxy test, and save action page-local.
- Verification after the FormSection slice: `npm run build` passed. Browser read-only smoke was attempted on `#/accounts`, but the in-app Browser rejected the local page action due to URL policy; no alternate browser/control workaround was used. This slice is build-verified only until the next allowed manual or browser smoke pass.
- Added `web-vue/src/components/ai/ImportModePanel.vue` as the shared title/description card for account import modes. Accounts OAuth, Access Token, Session JSON, Codex JSON, CPA JSON, Remote CPA, and Sub2API import sections now use it for their repeated explanatory panel only.
- Verification after the ImportModePanel slice: `npm run build` passed. The OAuth authorize URL content remains page-local because it is dynamic generated content, not an import-mode description shell. No import, OAuth finish, file read, remote CPA/Sub2API load, account refresh, or other write/external action was executed.
- Added `web-vue/src/components/ai/InfoCard.vue` as the shared read-only information card shell. `Docs.vue` now uses it for authentication notes, model catalog cards, operations notes, risk/smoke cards, and the hidden image-task notice.
- Verification after the InfoCard slice: `npm run build` passed, and a static scan confirmed the repeated `rounded-2xl border ... p-5` documentation card wrappers were removed from `Docs.vue`. This component is intentionally read-only and does not replace `FormSection` or `ImportModePanel`.
- Added `web-vue/src/components/ai/CodeBlock.vue` as the shared curl/API example display shell. `Docs.vue` now uses it for the three API examples while keeping example strings and model catalog state page-local.
- Verification after the CodeBlock slice: `npm run build` passed. No API calls, settings save, account action, proxy test, image action, or log mutation was executed.
- Added `web-vue/src/components/ai/DetailFieldCard.vue` as the shared read-only field card used by the Logs detail drawer. It only controls label/value/copy-button presentation; log parsing and copy behavior remain page-local.
- Verification after the DetailFieldCard slice: `npm run build` passed; CodeGraph is up to date; browser read-only smoke opened the first Logs detail drawer and rendered 17 `.detail-field-card` nodes, 3 copy buttons, no horizontal overflow, and console error count 0. No log delete, clear, export, account action, proxy action, settings save, or image mutation was executed.
- Added `web-vue/src/components/ai/DetailTextBlock.vue` as the shared long-text block used by the Logs detail drawer for request text, error text, upstream text replies, result URLs, and raw JSON. It only controls title/tone/text-scroll/max-height/copy presentation; selected-log state, copy behavior, log parsing, and log actions remain page-local.
- Verification after the DetailTextBlock slice: `npm run build` passed. Browser read-only smoke opened and closed the first Logs detail drawer, rendered 17 `.detail-field-card` nodes and 2 `.detail-text-block` nodes, including `Raw detail JSON` with `max-height=24rem`; after close it left zero modal/detail nodes, had no horizontal overflow, and console error count was 0. No log delete, clear, export, account action, proxy action, settings save, or image mutation was executed.
- Added `web-vue/src/components/ai/DetailImagePreview.vue` as the shared image-preview grid used by the Logs detail drawer. It only controls title/count, thumbnail grid, filename display, and broken-image fallback; `Logs.vue` still owns URL normalization, selected log state, broken URL tracking, detail opening, and all log actions.
- Verification after the DetailImagePreview slice: `npm run build` passed. Browser read-only smoke opened the first visible Logs detail drawer, but the current first-page data had no image URLs, so `.detail-image-preview` naturally rendered 0 nodes; this slice is build-verified and empty-data smoke-verified, while positive image-preview rendering still depends on finding a log row with image URLs. No log delete, clear, export, account action, proxy action, settings save, or image mutation was executed.
- Added `web-vue/src/components/ai/LogImagePreviewCell.vue` as the shared display cell for the Logs table image column. It only controls first-thumbnail rendering, broken-image fallback, image-count chip, and empty state; `Logs.vue` still owns broken URL tracking, detail opening, log parsing, and all log actions.
- Verification after the LogImagePreviewCell slice: `npm run build` passed; CodeGraph status is up to date. Browser read-only smoke on `#/logs` showed 5 log rows, 5 `.log-image-preview-cell__empty` nodes, 0 preview buttons because current `data/logs.jsonl` first-page rows have no image URLs, no horizontal overflow, and console error count 0. No log delete, clear, export, account action, proxy action, settings save, or image mutation was executed.
- Added `web-vue/src/components/ai/GalleryImageCard.vue` as the shared display card for the Gallery image grid. It owns only the thumbnail/fallback shell, selected/expired visual state, overlay buttons, filename/meta/countdown and one-line tags; `Gallery.vue` still owns selection state, preview modal, copy/download/delete/tag editing, broken-image tracking, pagination, filtering and storage actions.
- Verification after the GalleryImageCard slice: `npm run build` passed; CodeGraph sync completed. Browser read-only smoke on `#/gallery` stabilized after async loading and showed 24 `.gallery-image-card` nodes, 24 `.gallery-item` nodes, one `.image-grid`, no horizontal overflow, no loading spinner, and console error count 0. No image preview click, copy, tag edit, download, delete, cleanup, compress, settings save, account action or proxy action was executed.
- Added `web-vue/src/components/ai/GalleryLightbox.vue` as the shared media preview shell for the Gallery image preview. It owns only the Teleport overlay, preview image layout, close button and visible action-button presentation; `Gallery.vue` still owns the selected preview file, URL formatting, download, copy, tag editor opening and all image mutations.
- Verification after the GalleryLightbox slice: `npm run build` passed. Browser read-only smoke on `#/gallery` opened the first visible image preview and then closed it; the page showed 24 gallery cards, one `.lightbox`, one `.lightbox-media`, three `.lightbox-btn` nodes, one close button, no horizontal overflow, then zero lightbox nodes after close, with console error count 0. No download, copy, tag edit, delete, cleanup, compress, settings save, account action or proxy action was executed.
- 2026-06-08 reuse rule added: before creating page-local UI, check existing project components and `nanocat-ui`; prefer prop/slot extension over duplicate components. Logs large image preview now reuses `GalleryLightbox.vue` with `showActions=false` instead of keeping a second page-local lightbox. The drawer thumbnail grid remains `DetailImagePreview.vue` because it is a different in-drawer grid surface, not the full-screen preview shell.
- Added `web-vue/src/components/ai/GalleryTagEditorModal.vue` as the shared Gallery tag editor shell. It owns the modal composition, thumbnail, tag input layout, existing-tag chip presentation and footer buttons; `Gallery.vue` still owns the draft state, tag parsing/toggling, close guard, save request, tag refresh, preview-file sync and all image mutations.
- Verification after the GalleryTagEditorModal slice: `npm run build` passed. Browser read-only smoke on `#/gallery` opened the first visible image tag editor and then closed it; the page showed 24 tag-edit triggers, one `.modal-shell`, one `.modal-header`, one `.modal-footer`, no horizontal overflow, then zero modal nodes after close, with console error count 0. No save, clear, tag toggle, download, copy, delete, cleanup, compress, settings save, account action or proxy action was executed.
- Extended `web-vue/src/components/ai/StateBlock.vue` with an optional `media` slot and moved Gallery loading/empty/error states onto it. `Gallery.vue` now only keeps page-specific height and text while the spinner/icon placement and state shell come from the shared component.
- Verification after the Gallery StateBlock slice: `npm run build` passed. Browser read-only smoke on `#/gallery` showed 24 `.gallery-image-card` nodes, one `.image-grid`, zero active `.gallery-state-block` nodes in the current non-empty data state, no horizontal overflow, and console error count 0. No image preview, copy, download, delete, tag save, cleanup, compress, settings save, account action or proxy action was executed.
- Extended `web-vue/src/components/ai/FormSection.vue` with a `surface` option and moved Proxy global proxy input/test-result cards onto it. `Proxy.vue` still owns global proxy save, clear and external test actions; the component only controls card/background surface, border, radius, padding and density.
- Verification after the Proxy FormSection surface slice: `npm run build` passed. Browser read-only smoke on `#/proxy` showed two `.form-section` nodes, two `.page-panel` blocks, no horizontal overflow, and console error count 0. No proxy save, external proxy test, group create/edit/delete, settings save, account action, image action or log mutation was executed.
- Continued the Proxy FormSection slice inside the proxy-group modal: the proxy-node editor rows now use `FormSection surface="background"` and the outer "代理节点" area is just a lightweight header/list, avoiding page-local nested card shells.
- Verification after the Proxy node FormSection slice: `npm run build` passed. Browser read-only smoke opened and closed "新建代理组" without saving or testing; the modal showed one `.form-section--surface-background`, zero old node-card wrappers, no horizontal overflow, and console error count 0. No proxy save, external proxy test, node delete, group create/edit/delete, settings save, account action, image action or log mutation was executed.
- Accounts account-group management list items now use `InfoCard` for the repeated read-only group card shell. The account-group form, edit/delete buttons, save action and delete confirmation remain in `Accounts.vue`.
- Verification after the Accounts account-group InfoCard slice: `npm run build` passed. Browser read-only smoke opened and closed "账号组管理" without saving, editing or deleting; current local data had no account groups, so the empty `StateBlock` rendered, old account-group card wrappers were 0, no horizontal overflow, and console error count 0.
- Public uptime and admin monitor service status cards now share `web-vue/src/components/ai/ServiceStatusCard.vue`. The shared component only owns the read-only status card, badge, heartbeat bars and tooltip styling; `useUptimeStatus` still owns polling, data mapping and API access.
- Verification after the ServiceStatusCard slice: `npm run build` passed. Browser read-only smoke covered `#/public/logs`, `#/public/uptime`, and `#/monitor`; each page had one `.page-panel`, no horizontal overflow, and console error count 0. The current local uptime dataset was empty, so positive service-card rendering is build-verified and will be visually checked when real uptime data exists. No account action, proxy action, settings save, image mutation or log mutation was executed.
- PublicLogs stats now also use `MetricStrip.vue`, and `MetricStrip` gained an optional `valueStyle` field so the public load color from the backend can still be applied without page-local metric-card DOM.
- Verification after the PublicLogs MetricStrip slice: `npm run build` passed. Browser read-only smoke on `#/public/logs` showed one `.metric-strip`, eight metric cards, zero legacy `.ui-card-sm` nodes in that page, no horizontal overflow, and console error count 0. No log delete, export, clear, account action, proxy action, settings save or image mutation was executed.
- PublicLogs summary/action strip now uses `InfoCard.vue` for the read-only "展示最近 N 条会话日志 / 开始对话" shell, replacing one more page-local rounded border block while keeping the chat link and public-log polling logic page-local.
- Verification after the PublicLogs InfoCard slice: `npm run build` passed. Browser read-only smoke on `#/public/logs` showed one `.info-card`, one `.metric-strip`, eight metric cards, zero legacy `.ui-card-sm` nodes, no horizontal overflow, and console error count 0. No log delete, export, clear, account action, proxy action, settings save or image mutation was executed.
- Added `web-vue/src/components/ai/SelectableListPanel.vue` as the shared scrollable selection-list shell for account import flows. Accounts Remote CPA file selection and Sub2API account selection now use it for the list border, max-height, row padding, hover state and empty state; server loading, checkbox state, import progress and import requests remain page-local.
- Verification after the SelectableListPanel slice: `npm run build` passed. Browser read-only smoke on `#/accounts` opened and closed the import/add modal through the OAuth mode, showed one modal while open and zero after close, no horizontal overflow, and console error count 0. Remote CPA/Sub2API load buttons and import actions were not clicked.
- Accounts OAuth authorize URL now uses `InfoCard.vue` for the generated read-only URL shell, while copy/reopen/regenerate/finish-import actions remain in `Accounts.vue`. The refresh-progress modal now uses `MetricStrip.vue` for its compact metric/status pair instead of page-local mini cards.
- Verification after the Accounts OAuth/progress shell slice: `npm run build` passed. Browser read-only smoke on `#/accounts` showed the page title, no horizontal overflow, zero console errors, and no legacy auth/progress card wrappers in the default state. The OAuth URL card and refresh-progress metrics are conditionally rendered; no OAuth generation, import, account refresh, batch action, proxy test, export, delete or other write/external action was executed.
- Added `web-vue/src/components/ai/ProxyNodeSummaryCard.vue` as the proxy-table node summary shell. It owns the node name, enabled/disabled label, URL credential masking and compact card styling; proxy-group health text, test actions, save/delete/toggle behavior and confirmation prompts remain in `Proxy.vue`.
- Verification after the ProxyNodeSummaryCard slice: `npm run build` passed, and static scan confirmed `Proxy.vue` no longer contains the old `rounded-lg border border-border bg-card px-2.5 py-2` node-card wrapper or the page-local `maskProxy()` helper. Browser read-only smoke was attempted on `localhost` and `127.0.0.1`, but local navigation was blocked by the client, so this slice is build/static-verified only. No proxy save, proxy test, proxy toggle, proxy delete, account action, settings save, image action or log mutation was executed.
- 2026-06-08 read-only smoke was re-run with the local API started as `uv run uvicorn main:app --host 127.0.0.1 --port 8000 --lifespan off --no-access-log`. This intentionally avoids startup cleanup, backup scheduling, and account watcher refresh while still serving API reads for the control panel.
- Authenticated route smoke covered `#/`, `#/accounts`, `#/logs`, `#/gallery`, `#/proxy`, `#/settings`, and `#/docs`: every route mounted behind auth, horizontal overflow was 0, and browser console error count was 0. The current local data snapshot is accounts `total=0`, call logs `total=5`, runtime logs `total=0`, gallery `total=997` with 24 first-page cards, and proxy groups `0`.
- No real account import/refresh/re-login/delete/export, OAuth generation or finish, proxy save/test/delete/toggle, settings save, image delete/download/cleanup/compress/tag save, or log delete/clear/export was executed in this smoke.
- Added `web-vue/src/components/ai/SurfaceBox.vue` as a small read-only surface shell for repeated border/radius/background display blocks. `Accounts.vue` now uses it for proxy-mode hint text, current-proxy summary, account-group enabled row, OAuth authorize URL text, and refresh-progress error text; account fields, proxy mode changes, account-group save, OAuth generation/finish, copy/reopen actions, and refresh progress logic remain page-local.
- Verification after the SurfaceBox slice: `npm run build` passed. Browser read-only smoke on `#/accounts` showed the page mounted with no horizontal overflow and console error count 0; opening and closing "账号组管理" rendered one `.surface-box` in the modal, with no save/edit/delete/import/refresh/proxy test/export action executed.
- Added `web-vue/src/components/ai/ProgressBar.vue` as the shared 0-100 progress display. It is currently used by the Accounts refresh-progress modal; Gallery's old storage usage progress bar was removed from the main image-management page because it looked like fake progress and did not map to a user-triggered operation.
- Verification after the ProgressBar slice: `npm run build` passed. Browser read-only smoke on `#/accounts` and `#/gallery` showed no horizontal overflow and console error count 0. The Accounts progress bar remains conditionally rendered behind the refresh-progress modal and was build-verified only, because opening it requires a real account refresh/batch action.
- Added `web-vue/src/components/ai/StateBadge.vue` as the shared small status badge for success/danger/warning/muted labels. Accounts account-group enabled labels, Proxy proxy-group enabled labels, Logs call-log status labels, and Logs runtime-log level labels now use it instead of page-local rounded/border/background class strings; status mapping and all actions remain page-local.
- Verification after the StateBadge slice: `npm run build` passed. Browser read-only smoke covered `#/logs`, `#/accounts`, and `#/proxy`; Logs rendered 5 `.state-badge` nodes on the current call-log page, all three routes had no horizontal overflow and console error count 0. No log delete/clear/export, account import/refresh/delete/export, proxy save/test/delete/toggle, settings save, or image mutation was executed.
- Added `web-vue/src/components/ai/MetaChip.vue` as the shared weak metadata label adapter. It wraps `nanocat-ui` `MetaChip` and only maps this project's `xs/default/muted` aliases; AppShell version/API-model labels, Accounts selection summary counts, Docs model/risk/status labels, Logs type/source labels, Gallery storage/cleanup labels, old ImageTasks task metadata, and LogImagePreviewCell image-count labels now use it instead of raw `ui-chip` spans or direct page/component-level `nanocat-ui` chip imports. All label content and actions remain page-local.
- Verification after the MetaChip slice: `npm run build` passed and `rg -n "ui-chip" web-vue/src/views web-vue/src/layouts web-vue/src/components/ai` returned no matches. Browser read-only smoke covered `#/accounts`, `#/logs`, `#/gallery`, and `#/docs`; each route rendered `.ai-meta-chip` nodes, had no horizontal overflow, and local app console error count was 0. The API-info modal model chips are build-verified through AppShell; no copy, account, proxy, settings, image, task, or log mutation was executed.

## 2026-06-08 Navigation, Logs, Gallery, Debug 收口

- 主导航收口为：概览中心、画图、账号管理、日志管理、图片管理、代理管理、系统设置；监控状态和文档教程保留隐藏路由，避免主线入口过多。
- 调试中心恢复为独立底部/工具入口，参考旧 `web/src/app/debug` 的搜索、Skills 搜索、PPT 生成、PSD 生成和对话能力。真实搜索、PPT/PSD、对话请求属于 R3，smoke 默认不点击。
- 概览中心底部恢复轻量画图面板，但只走 `/api/image-tasks/*` 异步任务，不直接等待上游长生图请求。真实提交属于 R3。
- 日志管理继续区分调用日志和运行日志：调用日志保留分页表格与详情抽屉；运行日志采用接近旧版的 raw `pre` 输出面板，更接近容器运行日志阅读方式，不再额外渲染成伪终端 chrome。
- 图片管理去掉主界面的保留策略、存储维护和存储占用进度条；图片页保留筛选、分页、预览、标签、选择和批量动作。后端维护接口暂不删除。
- 日志和图片分页共用 `ListPagination.vue`，page size 菜单默认向下打开；账号、日志、图片都不再各自写分页按钮样式。
- 批量删除/下载这类动作已经使用 `OperationProgressModal` 给出进度反馈；日志和图片接口是一次性请求，弹窗只显示已提交/已处理，不像账号批量刷新那样支持逐批停止。由于它们有副作用，自动 smoke 只验证弹窗/按钮状态，不执行真实删除、下载或清理。
- 系统设置外部账号源改成“列表 + 新增/编辑弹窗”：CPA 测试读取远程文件列表，Sub2API 测试读取远程分组；这些都会访问外部服务，属于 R3，自动 smoke 不点击。

## 2026-06-08 Image Latency Read-only Diagnosis

- 本次没有触发新的真实画图，只读取 `data/logs.jsonl` 和后端调试日志。
- 最近几条图片请求明显慢于文本请求：图片成功耗时约 165s、335s、459s、528s，失败请求约 260s 到 377s；同时间段文本调用多在 4.6s 到 27s。
- 失败证据集中在上游和图片资产落地阶段：`curl: (56) Connection closed abruptly`、`response.failed/server_error`、`No image result found in response`、`image_poll_hit_no_settle`、`message_preview: {"skipped_mainline":true}`。
- 同一个账号 `chinaboywjh@gmail.com` 有成功图片结果也有失败记录，所以不像单纯额度空了；前端分页、列表渲染和图片管理页面不是这次“生图慢”的主要原因。
- 当前判断：慢主要来自上游图像生成/SSE 等待/文件资产 settle 或网络代理链路不稳定。要继续确认，需要指定测试账号和代理组后做 R3 小范围真实 smoke。

## 2026-06-08 Read-only Smoke Follow-up

- `npm run build` 已通过；`codegraph status D:\chatgpt2api` 显示索引 up to date。
- 只读浏览器 smoke 覆盖 `#/`、`#/accounts`、`#/logs`、`#/gallery`、`#/proxy`、`#/settings`、`#/debug`：主导航顺序为概览中心、账号管理、日志管理、图片管理、代理管理、系统设置，调试中心留在底部工具入口；监控状态和文档教程没有出现在主导航。
- 日志管理已确认：调用日志保留分页表格；运行日志切换后显示 `.runtime-raw-panel` 原始日志面板，自动刷新只在运行日志视图出现，调用日志不显示删除以外的运行日志控件。
- 日志详情已确认：点调用日志里的缩略图会打开站内大图预览，不会跳外链；点背景会先关闭大图预览，再关闭详情抽屉。
- 图片管理已确认：主界面没有保留策略、存储维护或假的存储进度条；分页继续复用 `ListPagination`。
- 系统设置外部账号源已确认：CPA/Sub2API 以列表方式展示，新增/编辑走 `ModalShell + ModalHeader + ModalFooter` 弹窗；测试按钮保留，但自动 smoke 不点击，因为会访问外部服务。
- 日志和图片的删除/下载进度弹窗仍是一次性请求反馈，只能显示“已提交/已处理”。它们不是账号批量刷新那种可分批停止任务；如果后续要完全对齐账号页的停止能力，需要后端新增 job/progress/cancel 接口。

## 2026-06-08 Logs Deletion and Card Radius Hotfix

- 日志管理主操作区移除“清空”入口，避免和“删除所选”靠得太近造成误操作。前端 `logsApi.clear()` helper 已移除；日志页只保留单条删除和所选删除。
- “删除所选”前端只会提交当前已加载列表里真实存在的 `selectedDeletableLogIds`，不会把旧筛选/旧分页残留的选中 ID 带到删除请求里。
- `LogService.delete()` 新增回归测试：空 ID 列表不会删除任何日志；重复/空/不存在 ID 与一个真实 ID 混合提交时，只删除匹配的那一条。
- 运行日志从 `.runtime-terminal` 伪终端改回接近旧版的 `.runtime-raw-panel + pre` 原始日志面板，旧 `runtime-terminal__footer` 类名也已清掉；调用日志表格和详情抽屉不变。
- `MetricStrip` 卡片圆角恢复到 16px，图库图片卡和图库预览默认圆角恢复到 16px；概览画图面板里的任务卡恢复 16px，输入/预览控件保持 12px，避免继续偏离原版 `rounded-2xl` 风格。
- 概览中心顶部统计卡改回原版 `nanocat-ui StatCard`，不再使用 `MetricStrip` 的 right-icon 变体；右上角图标尺寸和位置由原版组件控制，避免图标过大。
- 验证：`uv run python -m unittest test.test_log_service` 通过 7 个用例；`npm run build` 通过。浏览器只读检查确认：日志页按钮区没有“清空”，`删除所选` 仍存在且无横向溢出；概览统计卡/画图任务卡、图片管理统计卡/图片卡圆角均为 16px，相关页面横向溢出为 0。`python -m pytest test/test_log_service.py` 和 `uv run pytest test/test_log_service.py` 因本机/项目环境未安装 `pytest` 入口无法运行，已改用该测试文件自身的 `unittest` 入口。

## 2026-06-08 Logs Image Preview Reuse

- 日志详情图片大图继续复用 `GalleryLightbox.vue`，不新增日志页私有 lightbox；组件新增动作开关，Gallery 保持下载/复制/标签，Logs 只开放下载和复制链接。
- 日志详情暂不显示标签按钮，因为日志图片可能只是结果 URL 或临时资产，不一定已经进入图片管理索引；等日志图片能可靠映射到 `GalleryFile.path` 后再开放标签编辑。
- 日志详情缩略图从 `16:9 + cover` 改为 `4:3 + contain`，两张图时桌面端仍两列、移动端一列，缩略图尽量展示完整比例而不是裁掉证据区域。

## 2026-06-08 Logs Detail Field Density

- 日志详情字段从原始键名平铺改为“关键信息 / 诊断字段”分组：关键信息保留状态、接口、模型、耗时、时间、账号和密钥；诊断字段只在有真实值时展示。
- 成功日志不再展示 `status_code`、`conversation_id`、`error_code`、`stage`、`reason`、`request_shape`、`tool_invoked`、`blocked`、`upstream_message_len` 这类空字段，避免一屏 `-` 占位置。
- `DetailFieldCard.vue` 新增 `variant="row"` 紧凑展示，日志详情分组内使用 row 变体，避免卡片套卡片和字段间距过大。

## 2026-06-09 Image Drawing History Polish

- 外层侧边栏底部声明块已恢复为接近 `D:\gemini2api\frontend` 的灰底圆角说明样式，只保留控制台声明，不在全局侧边栏展示画图额度。
- 普通 `gpt-image-2` 的 1K 比例补齐为 `1:1`、`2:3`、`3:2`、`3:4`、`4:3`、`9:16`、`16:9`；`codex-gpt-image-2`、`gpt-image-2-codex` 以及 plus/team/pro 派生 Codex 模型继续开放 2K/4K 档位。
- 画图历史支持删除整段对话，也支持删除单条对话记录；删除只移除当前浏览器里的本地对话和对应 task id，不调用后端真实删除接口，避免误删服务端日志或图库资产。
- 清空画图历史改为先弹确认框；确认后清空 `imageTaskConversations`、`imageTaskLocalIds` 和 `imageTaskActiveConversationId`。刷新时只按本地保存的 task id 拉取状态，本地没有 id 就显示空历史，不再把服务端旧任务自动挂回。
- 删除和清空的确认文案已改成“当前浏览器里的历史”，明确不会删除服务器任务或图片；历史里的“回填提示词”只回填提示词和参考图，不再自动替用户切换模型、比例、分辨率或质量。
- 成功生成后的图片预览去掉额外灰色背景，并从 masonry/columns 改为紧凑附件式排版；等待中、失败和无图片 URL 状态仍保留背景承载提示。下载按钮改为显式 blob 下载，不再失败后打开原图 URL。
- 画图结果删除/清空仍不触发真实生图、账号刷新、代理测试或外部写入；真实画图 smoke 继续归入 R3，等指定测试账号和代理组后再做。

## 2026-06-09 Codex 2K/4K Failure Diagnosis

- 支持口径已收紧为“分链路”：普通 `gpt-image-2` 的尺寸/质量只作为 ChatGPT Web 图片链路的 prompt hint，前端只开放 `auto/1K`；Codex 图片模型才把 `size/quality` 作为 `/backend-api/codex/responses` image tool 的真实参数，前端因此只在 Codex 模型上开放 2K/4K。
- 最近失败样本属于 `plus-codex-gpt-image-2 + 2160x3840`。上游 HTTP 返回 200，但 SSE 事件里出现 `error.code=server_error` 和 `response.failed`，没有图片资产；同账号附近有普通图片请求成功，所以不像前端没传参数，也不像整体带宽或账号池全挂。
- 后端新增 Codex SSE 错误识别：无图片结果时会优先提取上游 `error`，任务/调用日志会保留 `upstream_error_type` 和 `upstream_request_id`。日志详情和任务主错误文案会显示 request id，便于后续拿 request id 判断是 OpenAI 上游工具失败还是本地链路失败。
- 画图页 4K 选项增加弱风险提示：4K 会走 Codex 图片工具，上游更容易 `server_error`；失败时建议先降到 1K 或 2K 排除分辨率触发的上游失败。
- 图片下载收口到 `web-vue/src/lib/downloads.ts`：画图结果、图片管理单张下载和日志详情图片下载都优先用后端 `/api/images/download/{path}` 拉取附件 blob，再触发 `a[download]`；结果资产新增 `path` 字段给前端下载使用。老任务没有 `path` 时会从 `/images/...` URL 尽量反推，外部 URL 无法被浏览器读取时只提示失败，不再 fallback 打开原图 URL。后续新增图片下载入口必须先复用这个 helper，不要再手写 `<a target="_blank">`。

## 2026-06-10 Gallery Invalid Preview Diagnosis

- 图片管理里出现的一批“无法预览”不是前端组件问题，而是 `data/images/2026/06/09` 里有 5 个 15B 的假 `.png` 文件，内容实际是文本 `generated image`，hash 因此都相同。
- 根因是测试曾把 `b"generated image"` 当作假图片 bytes 走进真实图库保存路径，污染了本地 `data/images` 和 `data/image_index.json`。
- 后端已加防线：`image_storage_service.save()` 保存前校验真实图片；`list_items()` 会跳过磁盘坏图并从索引剔除无效本地记录；`get_bytes()` 和 `has_local()` 不再把无效本地文件当图片返回。
- 协议层已把无效上游图片 payload 转成 `invalid_image_payload / receiving_image`，方便日志定位“上游返回的文件不是图片”。
- 测试已改为使用有效 1x1 PNG fixture 或 mock `image_storage_service.save()`，避免协议测试再次写入真实图库目录。
- 磁盘上的 5 个 15B 文件暂未自动删除；只有用户确认清理后，才删除这些明确识别出的假图文件。

## 2026-06-10 Image Task Output Count

- 画图任务链路已开放 `n=1..4`：`/api/image-tasks/generations` 的 JSON body、`/api/image-tasks/edits` 的 multipart/JSON body 都会把 `n` 传入 `ImageTaskService`，任务公开结构也会返回 `n`。
- 前端画图参数菜单新增“数量”选择，默认 1 张；生成和图生图都会发送同一个 `n`，结果继续按任务 `data[]` 渲染。
- 多参考图输入和多结果输出是两件事：`images`/`image`/`image_url` 控制参考图输入，`n` 控制输出数量。真实生图 smoke 仍属于 R3，需要指定测试账号和代理组后再执行。

## 2026-06-10 Test Governance and Storage Contract

- 默认后端回归已收口到 `python -m unittest discover -s test`：当前结果是 154 个测试通过、17 个 live HTTP smoke 默认跳过。
- 真实 localhost/上游测试改为显式开关：设置 `CHATGPT2API_RUN_LIVE_HTTP_TESTS=1` 后才运行 `test_v1_chat_completions`、`test_v1_images_generations`、`test_v1_images_edits`、`test_v1_messages`、`test_v1_models`、`test_v1_responses` 这类 live smoke。
- 测试辅助文件从 `test/utils.py` 改为 `test/helpers.py`，避免 `unittest discover -s test` 时遮蔽项目自己的 `utils` 包，导致 `utils.helper`、`utils.log` 等导入失败。
- SQLite 存储后端补齐 `list_accounts_page(...)`，当前按 `accounts.data` JSON 做过滤、统计和分页，用于支撑账号池分页契约和 1w 账号前的保守落地；如果真实数据量压测显示瓶颈，再迁移常用字段为列式索引。
- 验证：`python -m unittest test.test_database_storage` 通过；`python -m unittest discover -s test` 通过；`npm run build` 通过；`codegraph sync D:\chatgpt2api` 后 `codegraph status D:\chatgpt2api` 显示索引 up to date。

## 2026-06-10 Frontend Noise Smoke

- `test_v1_models.test_list_models_function` 改为 mock 上游模型列表和账号池，不再在默认单测里访问真实 ChatGPT 上游；`test_list_models_http` 继续由 live smoke 开关控制。
- Gallery 空态图标补齐 `@iconify/vue` 的 `Icon` import；ImageTasks 参数下拉和 Settings 存储模式下拉改为外层 wrapper 控宽，不再把 `class` 透传给 `nanocat-ui` `SelectMenu` 造成 Vue fragment warning。
- 干净新标签只读 smoke 覆盖 `#/gallery`、`#/image-tasks`、`#/settings`：三页均渲染，图像创作 footer 显示真实 `剩余 116 张`，本次开始时间后的 console warn/error 为 0。
- 验证：`python -m unittest discover -s test` 通过；`npm run build` 通过；后续真实导入、删除、代理测试、设置保存和生图仍按 R2/R3 手动 smoke，不在自动 smoke 里触发。

## 2026-06-10 Full Read-only Route Smoke

- 最新收口验证重新跑了 `git diff --check`、`python -m unittest discover -s test`、`npm run build`、`codegraph sync D:\chatgpt2api` 和 `codegraph status D:\chatgpt2api`。
- `git diff --check` 只有 Windows CRLF 提示，没有空白错误；默认后端回归 154 个测试通过、17 个 live HTTP smoke 默认跳过；前端生产构建通过。
- CodeGraph 索引已更新：401 files、6,854 nodes、13,906 edges、101 routes，状态为 up to date。
- 只读浏览器 smoke 覆盖 `#/`、`#/accounts`、`#/logs`、`#/gallery`、`#/image-tasks`、`#/proxy`、`#/settings`、`#/debug`：所有路由均能渲染主标题，console warn/error 为 0。
- 图像创作单独复查确认路由标题为“图像创作”，不是图片管理页残留；之前一次脚本读到旧页面，是导航后等待条件过宽导致的 smoke 脚本假阳性。
- 前端静态收口扫描确认 `web-vue/src/views`、`web-vue/src/layouts`、`web-vue/src/components` 下不再直接出现 `fetch(...)`、`axios.*`、裸 `apiClient` 或散落 `localStorage`；画图页 data URL 转 File 的逻辑抽到 `web-vue/src/lib/files.ts`。
- 本轮仍没有执行真实账号导入/刷新/删除/导出、代理测试/保存、设置保存、日志删除、图片删除/清理/下载或真实生图。
