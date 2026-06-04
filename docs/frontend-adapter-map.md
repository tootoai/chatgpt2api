# gemini-web2api 前端适配地图

## 可用前端基底

优先使用：

```text
D:\gemini2api\frontend
```

技术栈：

- Vue 3
- Vite
- TypeScript
- Pinia
- Vue Router
- Axios
- ECharts
- Tailwind CSS
- nanocat-ui

已核对版本：

- `package.json` version: `0.3.3`
- 源码目录：`src/api`、`src/views`、`src/layouts`、`src/stores`

不建议把这套 Vue 前端和当前 `web/` Next.js 前端混合。更清晰的方案是：以 Vue 前端为新控制台基底，重写 API module 和类型。

## 页面适配

| gemini 页面 | 是否保留 | chatgpt2api 用途 |
| --- | --- | --- |
| `Dashboard.vue` | 保留 | 概览中心，展示账号、图片、日志、存储图表 |
| `Accounts.vue` | 保留 | 账号池管理，改字段和操作 |
| `Logs.vue` | 保留并加强 | 日志管理、调用日志、图片失败详情、结果图片预览 |
| `Gallery.vue` | 保留 | 图片画廊，接 `/api/images` |
| `ImageTasks.vue` | 暂时隐藏 | 文件和 adapter 可保留，第一版不进导航，不作为主入口 |
| `Settings.vue` | 保留 | 设置中心，接 `/api/settings` |
| `Monitor.vue` | 可保留 | 健康检查、服务状态 |
| `Docs.vue` | 可替换 | 改成本项目接口说明或隐藏 |
| `PublicLogs.vue` | 暂缓 | 可后续做公开状态页 |
| `PublicUptime.vue` | 暂缓 | 可后续做公开健康页 |

## API 适配

| gemini 前端 API | 当前用途 | chatgpt2api 对应 |
| --- | --- | --- |
| `/login` | 管理员登录 | `/auth/login`，认证方式要改成 Bearer key |
| `/auth/status` | 登录状态检查 | 已补 `/auth/status`，前端只需要改成 Bearer key 认证 |
| `/admin/stats` | 概览图表 | 改接 `/api/dashboard` 聚合 |
| `/admin/accounts` | 账号管理 | `/api/accounts` |
| `/admin/log` | 日志中心 | `/api/logs` |
| `/admin/gallery` | 画廊 | `/api/images` |
| `/admin/settings` | 设置 | `/api/settings` |
| 代理分组接口 | 代理管理 | `/api/proxy/profiles*`，并通过 `/api/settings` 保存全局代理 |

## 类型适配

### 账号

gemini `ReverseAccount` 偏 cookie/lane/pro/thinking。chatgpt2api 账号字段应改为：

- `access_token`
- `type`
- `source_type`
- `status`
- `quota`
- `image_quota_unknown`
- `email`
- `user_id`
- `limits_progress`
- `default_model_slug`
- `restore_at`
- `success`
- `fail`
- `last_used_at`
- `proxy`

### 日志

gemini 日志有 `row_id`、`req_id`、`lane`、`stage`。chatgpt2api 日志应从 `SystemLog.detail` 提取：

- `endpoint`
- `model`
- `status`
- `request_text`
- `request_shape`
- `error`
- `urls`
- `account_email`
- `conversation_id`
- `duration_ms`

建议新前端把日志分成：

- 调用日志
- 账号日志
- 图片失败日志
- 运行日志，后续新增

### 图表

gemini Dashboard 当前图表：

- 模型请求分布
- 调用趋势
- 成功率趋势
- 平均响应时间
- 模型调用占比
- 模型使用排行

chatgpt2api 当前对齐原版 Dashboard 图表语义，只替换数据源：

- 模型请求分布：`logs.trend.model_requests`
- 调用趋势：`success_requests` / `failed_requests` / `rate_limited_requests`
- 成功率趋势：按 `total_requests` 和失败/限流序列计算
- 平均响应时间：`logs.trend.model_total_times`，单位由前端换算为秒展示
- 模型调用占比：按模型总调用数聚合
- 模型使用排行：按模型总调用数排序

## 迁移方式

推荐方式：

1. 复制 Vue 前端基底到新工作目录。
2. 保留布局、组件、图表主题。
3. 删除 Gemini 专有概念：
   - lane
   - fast/thinking/pro quota
   - snlm0e
   - cookie resolve
   - Gemini public display
4. 新建 chatgpt2api 类型。
5. 重写 API module。
6. 页面按 chatgpt2api 数据字段重新渲染。

不推荐方式：

- 不把后端强行改成 gemini 的 `/admin/*` 全套接口。
- 不在页面组件里直接做大量字段转换。
- 不继续维护 Vue 和 Next 两套正式前端。
- 不照抄 gemini 的密码登录、cookie lane、public display、Gemini quota 字段。
- 不照抄当前 Next 前端里没有后端实现的 `/api/proxy` 读写函数。
- 代理管理已改成真实后端接口：全局代理走 `/api/settings`，分组走 `/api/proxy/profiles*`，账号引用写 `profile:<id>`。

## 是否要新增后端接口

已新增少量聚合接口，但不要大改已有接口：

- `GET /auth/status`
- `GET /api/dashboard`
- 后续可选：`GET /api/runtime-logs`

这些接口只做聚合和展示，不改变核心业务。

## API adapter 改造顺序

1. `src/api/client.ts`
   - 改为自动附加 Bearer key。
   - 错误提取顺序兼容 `detail.error`、`error.message`、`message`。
2. `src/stores/auth.ts`
   - 改为保存本地 key。
   - `checkAuth` 直接接 `/auth/status`。
3. `src/types/api.ts`
   - 删除 Gemini 专有类型。
   - 增加 chatgpt2api 的 Account、SystemLog、ImageTask、ManagedImage、Settings。
4. `src/api/stats.ts`
   - 第一版直接接 `/api/dashboard`。
5. `src/api/reverseAccounts.ts`
   - 改名或重写为 `accounts.ts`。
6. `src/api/logs.ts`
   - 接 `/api/logs`，前端本地补 endpoint/status/account/conversation 筛选。
7. `src/api/gallery.ts`
   - 接 `/api/images*`。
8. `src/api/settings.ts`
   - 接 `/api/settings` 和测试类接口。
9. `src/api/imageTasks.ts`
   - 已接 `/api/image-tasks/*`，但第一版 Vue 控制台暂时隐藏图片任务入口。
   - 文件保留给后续任务化图片工作流，不再阻塞账号、日志、设置、画廊主链路。

## 当前迁移状态

- 新前端落点：`web-vue/`。
- 已接：`/auth/login`、`/auth/status`、`/api/dashboard`、`/api/settings`、`/version`、`/api/accounts`、`/api/logs`、`/api/images*`。
- 图片任务 adapter 已保留，但导航和路由已暂时隐藏；当前第一版不做本地画图/图片任务页。
- 已验证：`web-vue` 登录、路由守卫、Dashboard 聚合图表、账号/日志/画廊 adapter、`npm run build`。
- Dashboard 已从“图片请求分布/失败原因排行”改回原版模型图表：模型请求分布、调用趋势、成功率趋势、平均响应时间、模型调用占比、模型使用排行；后端 `/api/dashboard` 已补 `logs.trend` 时间桶。
- 账号页已从 Cookie/lane/SNlM0e 语义改成 access token、类型/来源、代理、图片额度、恢复时间、成功/失败计数和刷新账号信息。
- 账号页已按 `D:\gemini2api\frontend` 的列表分页模式接入 `ListPagination`，全选只作用于当前页。
- 账号行操作已按 `D:\gemini2api\frontend` 改成“编辑 + 更多”菜单，更多里保留刷新账号信息和图片额度、重置状态、启用/禁用、删除。
- 账号导入已改成统一弹窗，包含 OAuth、Access Token、Session JSON、Codex JSON、CPA JSON 文件、远程 CPA、Sub2API。
- 账号编辑里的代理已从原始输入框改成模式选择器：全局代理、强制直连、代理分组、自定义代理，保存值分别为 `""`、`direct`、`profile:<id>`、原始代理 URL。
- 日志页已改成服务端筛选和分页：`/api/logs` 接 status、endpoint、model、account、conversation_id、search、limit、offset，并返回 `total/facets/stats`。
- 代理页已接全局代理保存、`/api/proxy/test` 和代理分组 CRUD；后端代理解析支持 `direct` 和 `profile:<id>`。
- 设置页已去掉 Gemini 专有配置，改为 chatgpt2api 真实配置分组：基础连接、图片链路、账号和并发、缓存、审核、图片存储、备份。
- 待改：设置页测试按钮细节。
