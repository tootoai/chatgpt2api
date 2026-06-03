# gemini-web2api 前端适配地图

## 可用前端基底

优先使用：

```text
D:\gemini-web2api-2\gemini-web2api-main\frontend
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
| `Logs.vue` | 保留并加强 | 调用日志、图片失败详情、运行日志入口 |
| `Gallery.vue` | 保留 | 图片画廊，接 `/api/images` |
| `Settings.vue` | 保留 | 设置中心，接 `/api/settings` |
| `Monitor.vue` | 可保留 | 健康检查、服务状态 |
| `Docs.vue` | 可替换 | 改成本项目接口说明或隐藏 |
| `PublicLogs.vue` | 暂缓 | 可后续做公开状态页 |
| `PublicUptime.vue` | 暂缓 | 可后续做公开健康页 |

## API 适配

| gemini 前端 API | 当前用途 | chatgpt2api 对应 |
| --- | --- | --- |
| `/login` | 管理员登录 | `/auth/login`，认证方式要改成 Bearer key |
| `/auth/status` | 登录状态检查 | 建议新增 `/auth/status`，或前端用本地 session + `/version` |
| `/admin/stats` | 概览图表 | 建议新增 `/api/dashboard` 聚合 |
| `/admin/accounts` | 账号管理 | `/api/accounts` |
| `/admin/log` | 日志中心 | `/api/logs` |
| `/admin/gallery` | 画廊 | `/api/images` |
| `/admin/settings` | 设置 | `/api/settings` |

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

chatgpt2api 建议改成：

- 图片请求趋势
- 图片成功率趋势
- 失败原因排行
- 账号状态分布
- 账号失败排行
- 图片耗时分布
- 存储占用趋势，后续做

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

## 是否要新增后端接口

建议新增少量聚合接口，但不要大改已有接口：

- `GET /auth/status`
- `GET /api/dashboard`
- 可选：`GET /api/runtime-logs`

这些接口只做聚合和展示，不改变核心业务。

## API adapter 改造顺序

1. `src/api/client.ts`
   - 改为自动附加 Bearer key。
   - 错误提取顺序兼容 `detail.error`、`error.message`、`message`。
2. `src/stores/auth.ts`
   - 改为保存本地 key。
   - `checkAuth` 临时可用 `/version` 或新增 `/auth/status`。
3. `src/types/api.ts`
   - 删除 Gemini 专有类型。
   - 增加 chatgpt2api 的 Account、SystemLog、ImageTask、ManagedImage、Settings。
4. `src/api/stats.ts`
   - 第一版前端聚合，后续接 `/api/dashboard`。
5. `src/api/reverseAccounts.ts`
   - 改名或重写为 `accounts.ts`。
6. `src/api/logs.ts`
   - 接 `/api/logs`，前端本地补 endpoint/status/account/conversation 筛选。
7. `src/api/gallery.ts`
   - 接 `/api/images*`。
8. `src/api/settings.ts`
   - 接 `/api/settings` 和测试类接口。
9. 新增 `src/api/imageTasks.ts`
   - 接 `/api/image-tasks/*`。
