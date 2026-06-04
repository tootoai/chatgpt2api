# 前端重写状态板

更新时间：2026-06-04

## 当前方案

新控制台以 `D:\gemini2api\frontend` 的 Vue 结构、组件密度和交互方式为参考，但功能语义、字段和接口以 chatgpt2api 为准。也就是说：

- 外观和交互：参考 gemini2api 的 Vue 控制台。
- 数据和动作：优先对齐当前项目 `web/src` 和现有后端。
- 新前端落点：`web-vue/`，稳定后再考虑替换正式 `web/`。
- 第一版不做本地画图和图片任务入口，避免浏览器长请求卡住控制台。
- 已新增 `docs/frontend-interface-action-map.md` 作为前端接口与动作风险地图；后续 smoke 和 UI 补全按 R0-R4 风险等级执行。
- 2026-06-04 已完成 R0/R1 全页面只读 smoke，记录见 `docs/frontend-r0r1-smoke-20260604.md`。
- 2026-06-04 二次只读巡检已覆盖 Dashboard、Accounts、Logs、Gallery、Proxy、Settings、Docs；页面控制台 error 为 0。运行日志只读视图已补入日志管理和 smoke 记录。
- 2026-06-04 已新增 `docs/frontend-r2-r4-smoke-plan-20260604.md`，并在 Docs 页“风险说明”里展示当前验收状态和 R2 测试对象要求。
- 2026-06-04 已完成 R2/R3/R4 动作保护审计：OAuth 登录开始/完成、账号代理测试、远程 CPA 文件列表、Sub2API 账号列表、远程 CPA/Sub2API 导入、账号导出、单账号刷新、账号启用/禁用、全局代理保存、全局代理测试、代理分组测试、代理分组启停、系统设置总保存、图片保留天数、清理预估、图片存储测试、图片存储同步、备份测试、立即备份和 Sub2API 分组读取，都已在真实请求前加入确认弹窗；删除/清空/压缩/执行清理继续保留原有确认。
- 2026-06-04 前端构建已通过；浏览器只读验证覆盖 Accounts、Proxy、Gallery、Settings 四个改动页，控制台无错误。已实测 Accounts 导出全部、OAuth 生成 URL、Gallery 保存保留天数、Settings 保存系统设置、Settings 同步本地图片、Settings 测试 WebDAV、Settings 测试备份连接、Proxy 保存全局代理会先弹确认并可取消；OAuth 刷新后验证为取消即不生成授权 URL，未执行账号导入/真实写入/外部存储或代理测试。
- 2026-06-04 已对齐 R2 文档口径：普通编辑弹窗保存，例如账号编辑、代理分组编辑、图片标签编辑、CPA/Sub2API 连接编辑，点击保存即视为确认；批量、状态切换、导入、导出、外部测试、同步和删除仍按风险等级加确认。CodeGraph 已检查图库标签保存、批量下载、账号批量刷新和批量菜单入口，影响面均限制在预期页面内。
- 2026-06-04 浏览器只读确认主菜单不包含图片任务/本地画图入口，当前 Accounts 页面控制台错误为 0。
- 2026-06-04 已完成 `web-vue/src/api` 写入口静态审计：`POST`、`DELETE` 和 `apiClient.request({ method: 'DELETE' })` 均已映射到 `docs/frontend-interface-action-map.md`；图片任务写入口仍只保留代码文件，未开放主菜单和路由入口。
- 2026-06-04 删除未引用的旧日志 composable `web-vue/src/views/logsPage/useLogsPage.ts`，避免旧清理/分组逻辑干扰当前 `Logs.vue` 审计；重新同步 CodeGraph 并通过 `npm run build`。
- 2026-06-04 删除未引用的脚手架残留 `web-vue/src/stores/index.ts` 和 `web-vue/src/lib/utils.ts`，并移除 `class-variance-authority`、`clsx`、`tailwind-merge` 三个未使用依赖；重新通过 `npm run build`。
- 2026-06-04 完成第二轮风险动作代码审计：Accounts、Proxy、Settings、Gallery、Logs 的导入、导出、刷新、恢复、外部连接测试、同步、备份、删除、清理等真实请求均在请求前确认；账号编辑、代理分组编辑、图库标签编辑、CPA/Sub2API 连接编辑仍按 R2 规则作为普通表单保存，不额外叠加二次确认。
- 2026-06-04 将 API 401 拦截器改为入口注册的未授权处理器，避免 `api/client.ts` 动态导入 `auth store/router`；构建通过且不再出现 Vite 动态/静态混用提示。
- 2026-06-04 将 `Docs.vue` 从 gemini2api 销售/教程页改为 chatgpt2api 文档中心，展示接口示例、运维边界和风险等级；浏览器复核无旧 Gemini/nano-banana 展示文案，控制台错误为 0。
- 2026-06-04 补齐 Logs、Gallery、Settings 的加载失败静态提示：GET 失败时不再只依赖 toast，而会在空态/设置占位区显示失败原因和重试入口；Docs、Logs、Gallery、Settings 浏览器只读复核均无控制台错误。
- 2026-06-04 手测前收口检查：主导航和路由仍不包含图片任务/本地画图入口；概览中心只保留账号卡片、Header 接口信息和 6 张模型图表；Accounts、Proxy、Settings、Gallery、Logs 的真实写入、删除和外部测试入口均已确认有显式按钮或确认弹窗保护。`npm run build` 通过，`python -m unittest test.test_system_api test.test_log_service` 17 项通过，`codegraph status D:\chatgpt2api` 显示索引已最新。真实 R2/R3/R4 smoke 按当前决定暂缓，等手动测试或指定测试对象后再执行。
- 2026-06-04 Docker 打包入口已切换到 `web-vue/`：镜像构建阶段使用 `npm ci && npm run build` 生成 `web-vue/dist`，最终复制到后端 `web_dist`。`.dockerignore` 已排除 `web-vue/node_modules`、`web-vue/dist`、CodeGraph 数据库、截图产物和本地日志，避免打包上下文混入本地文件。

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
- 已有分页，默认 50，选项 20/50/100，当前页全选。
- 已有批量刷新进度弹窗，前端按 20 个一批提交。
- 导入弹窗已覆盖：OAuth、Access Token、Session JSON、Codex JSON、CPA JSON 文件、远程 CPA、Sub2API。
- 行操作已改成“编辑 + 更多”，更多里放刷新、重置、启用/禁用、删除等操作。
- 账号代理已支持全局代理、强制直连、代理分组、自定义代理。
- 已接恢复异常账号：顶部可恢复全部异常账号，批量菜单和行操作也可触发 `/api/accounts/re-login` 并展示进度。
- 已接真实导出：优先调用 `/api/accounts/export` 导出完整 OAuth/Codex 认证 JSON；如果账号缺少 refresh_token/id_token，则回退导出 Access Token 文本。
- 编辑账号弹窗已接代理测试：全局代理、自定义代理和代理分组分别走对应测试接口。
- 2026-06-04 已完成账号页非破坏烟测：主表字段、分页、当前页全选、底部批量菜单、导入弹窗 7 种模式切换、行内“编辑 + 更多”、编辑弹窗代理入口均可用；控制台无错误。截图在 `artifacts/accounts-smoke-start-20260604.png`、`artifacts/accounts-smoke-menu-edit-20260604.png`、`artifacts/accounts-import-modes-20260604.png`。
- 2026-06-04 已补 OAuth 登录开始/完成、账号导出和远程账号来源读取的确认保护；浏览器已验证“OAuth 生成 URL”、“导出全部”和“远程 CPA 加载文件”会先弹确认并可取消，Sub2API 加载按钮在当前环境禁用，待真实配置 smoke。
- 还需要真实账号 smoke：OAuth、CPA、Sub2API、批量刷新、恢复异常、导出下载和代理测试实际请求。

### 日志管理

- 已接 `GET /api/logs` 和 `POST /api/logs/delete`。
- 服务端筛选已支持 type、date、status、endpoint、model、account、conversation_id、search、limit、offset。
- 列表已对齐旧 `web/src` 主视图：时间、类型、令牌名称、调用耗时、状态、图片、简述、操作。
- 长 request/error、诊断字段、上游文本回复、raw JSON 已放到详情抽屉。
- `detail.urls` 已支持图片预览，坏图显示“无法预览”。
- 已补当前页勾选、全选、取消选择和“删除所选”确认弹窗，批量删除走 `/api/logs/delete`。
- 日志加载失败时，空态会显示失败原因，避免只靠 toast 排错。
- 运行日志已新增只读 `/api/runtime-logs`：内存来源读取项目统一 logger，文件来源会尝试读取常见部署日志路径或 `CHATGPT2API_RUNTIME_LOG_FILE` 指定路径；Docker stdout 仍需部署侧重定向/挂载文件才可完整展示。

### 图片画廊

- 已接 `GET /api/images`、删除、下载、标签、存储统计、压缩和清理。
- `/api/images` 已支持服务端分页、搜索、日期、媒体类型、标签筛选和 `total/counts/total_size` 统计；前端只在旧后端缺少分页字段时退回本地分页。
- 已支持分页、搜索、日期、标签、预览、复制 URL、单张/批量删除、批量 zip。
- 画廊加载失败时，空态会显示失败原因；坏图继续显示媒体兜底。
- Vite 已代理 `/images` 和 `/image-thumbnails`。
- 2026-06-04 已完成画廊非破坏 smoke：本地 1021 张图库下页面只渲染 24 张当前页，`/api/images?limit=2&offset=48` 返回 2 条并保留 `total=1021`；控制台无页面错误。浏览器截图接口曾因 CDP 截图超时失败，不影响页面状态检查。
- 2026-06-04 已补 WebDAV-only 代码级回归：本地缺失时原图响应、缩略图生成和批量 zip 都会通过 `image_storage_service.get_bytes` 读取远端内容；`download_images_zip` 重复定义已清理为单一实现。
- 2026-06-04 已统一画廊保留/过期口径：图库页按 `image_retention_days` 天数显示和计算过期，跟设置页和后端自动清理一致；旧字段 `basic.image_expire_hours` 只作为兼容写回。浏览器 smoke 显示 1021 张图库、当前页 24 张、倒计时为“天/小时”格式，截图在 `artifacts/gallery-retention-days-20260604.png`。
- 还需要真实环境 smoke：WebDAV-only 图片、批量 zip、清理策略和坏图降级。

### 代理管理

- 已接全局代理保存和 `/api/proxy/test`。
- 代理分组已接 `/api/proxy/profiles*`。
- 账号代理值约定：空值使用全局代理，`direct` 强制直连，`profile:<id>` 使用代理分组。
- 2026-06-04 已完成代理页非破坏 smoke：主视图、全局代理、分组统计、空状态、新建代理分组弹窗均可打开，控制台无错误；截图在 `artifacts/proxy-smoke-main-20260604.png` 和 `artifacts/proxy-smoke-create-modal-20260604.png`。
- 已补系统接口测试覆盖代理分组创建/列表/删除，以及 `/api/proxy/profiles/test` 的 profile 引用解析。
- 还需要 smoke：真实代理测试、账号引用代理分组后的图片请求链路。

### 设置中心

- 已去掉 Gemini/Nanobanana/音乐/视频等无关配置。
- 已改成 chatgpt2api 真实配置分组：基础连接、图片链路、账号和并发、缓存、提示词和审核、图片存储、备份。
- 已补图片存储测试/同步、备份测试/立即备份/历史删除、CPA 连接管理、Sub2API 连接管理和 Sub2API 分组读取。
- 图片存储测试/同步、备份测试/立即备份现在不再隐式保存表单；有未保存改动时会提示先保存，避免“点测试实际改配置”。
- 设置加载失败时，页面会显示失败原因和重新加载按钮，不再长时间停在“设置加载中”。
- 2026-06-04 已完成非破坏设置页 smoke：基础连接、图片链路、缓存、提示词和审核、图片存储、备份、CPA/Sub2API 连接管理均可加载，控制台无错误；截图在 `artifacts/settings-smoke-mid-20260604.png` 和 `artifacts/settings-smoke-bottom-20260604.png`。
- 还需要真实环境 smoke：WebDAV、R2 备份、CPA 列文件、Sub2API 读分组/读账号。

## 暂缓

- 图片任务/本地画图：第一版隐藏，后续必须走 `/api/image-tasks/*`，不要再让浏览器直接等待长图像请求。
- 注册机：第一版不接，后续从 `D:\codexzz\webfree_server` 单独任务化。
- 公开日志和公开 uptime：可后续恢复。
- 真正运行日志：已接 `/api/runtime-logs` 只读视图；如要看 Docker stdout/stderr，需要部署侧写入文件并通过 `CHATGPT2API_RUNTIME_LOG_FILE` 挂载。

## 下一步顺序

1. 先形成可手测检查点：保留当前前端改写结果，准备提交/打包，后续问题按手动测试反馈逐项修。
2. R2 小范围写入 smoke：用明确测试对象验证保存设置、账号编辑、标签编辑、代理分组编辑；普通编辑弹窗点击保存即视为确认，不额外叠加二次确认。
3. R3 外部副作用 smoke：OAuth、CPA、Sub2API、WebDAV、R2、代理测试、批量刷新和恢复异常账号，需要真实配置和明确确认。
4. R4 破坏性 smoke：只在明确测试数据上验证删除账号、删除日志、删除图片、清理图库、删除备份。
5. 后端缺口：运行日志只读链路已接入；图片任务/本地画图继续隐藏，后续恢复时走 `/api/image-tasks/*`。

R2 真测前需要先指定或临时创建这些测试对象，避免误改真实账号池：

- 测试账号：允许编辑 access token、代理、状态、配额并可恢复/删除的账号 ID。
- 测试代理分组：允许创建、编辑、停用和删除的 `profile:<id>`。
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
