# 前后端缺口清单

这份清单记录新 Vue 控制台落地前需要处理的接口差异。它分清楚当前已有、建议新增、不能照抄三类，防止迁移时误判。

## 当前已有，前端可以直接接

| 功能 | 接口 | 说明 |
| --- | --- | --- |
| 登录 | `POST /auth/login` | Bearer key 登录，不是账号密码登录。 |
| 登录状态 | `GET /auth/status` | 返回 `{ ok, authenticated, version }`，认证成功时附带角色和主体信息。 |
| 版本 | `GET /version` | 返回 `{ "version": "..." }`。 |
| 健康状态 | `GET /health?format=json` | 包含号池统计和存储健康，可作为概览临时数据源。 |
| 概览聚合 | `GET /api/dashboard?time_range=24h` | 返回账号、存储、调用日志聚合，并包含 `logs.trend` 模型时间桶，供新 Dashboard 直接消费。 |
| 账号列表 | `GET /api/accounts` | 返回 `{ items }`。 |
| 账号新增/删除/更新 | `/api/accounts*` | 支持 token、OAuth 账号、刷新、重登、完整认证导出；Vue 账号页已接恢复异常进度和导出回退。 |
| 用户密钥 | `/api/auth/users` | 管理本服务 user key。 |
| 图片任务 | `/api/image-tasks/*` | 接口已存在，Vue 控制台已恢复“画图”入口；普通 user key 登录后只进入这个页面。 |
| 图片画廊 | `/api/images*` | 列表、删除、下载、标签、存储统计、压缩和按目标剩余空间清理。 |
| 日志 | `/api/logs` | 支持 type/date/status/endpoint/model/account/conversation/search 服务端筛选，并返回分页、facets 和 stats。 |
| 设置 | `/api/settings` | 返回完整配置对象。 |
| 代理管理 | `/api/proxy/test`、`/api/proxy/groups*` | 新控制台前台支持全局代理测试、代理组 CRUD、`group:<id>` 账号引用和 `direct` 强制直连。旧 profile 接口仅作后端兼容事实，不作为前台方案。 |
| 备份 | `/api/backups*` | 可接设置页或备份页。 |

## 后续建议新增，但不阻塞第一版

| 建议接口 | 用途 | 原因 |
| --- | --- | --- |
| 图片任务诊断字段 | `account_email`、`error_code`、`error_stage`、`can_resume_poll` | 让任务页能直接判断失败原因和下一步动作。 |

## 不能照抄的旧前端接口

当前 `web/src/lib/api.ts` 和 gemini 前端里都有一些不完全匹配 chatgpt2api 后端的接口。新前端不要直接复制。

| 来源 | 接口 | 问题 |
| --- | --- | --- |
| gemini 前端 | `/login` | 它是密码登录；chatgpt2api 是 `POST /auth/login` + Bearer key。 |
| gemini 前端 | `/auth/status` | chatgpt2api 已新增同名接口，但认证方式仍是 Bearer key。 |
| gemini 前端 | `/admin/stats` | 不照抄，改成 chatgpt2api 的 `/api/dashboard`。 |
| gemini 前端 | `/admin/accounts` | chatgpt2api 是 `/api/accounts`，字段也不同。 |
| gemini 前端 | `/admin/log` | chatgpt2api 是 `/api/logs`，日志结构不同。 |
| 当前 Next 前端 | `/api/proxy` | 不照抄旧的虚拟读写接口；新 Vue 前端使用 `/api/settings` 保存全局代理，使用 `/api/proxy/groups*` 管理多节点代理组。`/api/proxy/profiles*` 仅作为历史 profile 兼容事实保留，不作为前台主方案。 |

## 图片任务字段缺口

当前 `services/image_task_service.py` 的公开任务字段主要是：

- `id`
- `status`
- `mode`
- `model`
- `size`
- `quality`
- `created_at`
- `updated_at`
- `conversation_id`，只在部分错误里出现
- `data`
- `usage`
- `error`
- `progress`
- `duration_ms`
- `elapsed_secs`

新前端想做更强诊断时，不要假设以下字段已经存在：

- `account_email`
- `error_code`
- `error_stage`
- `can_resume_poll`
- `request_text`
- `client_task_id`，当前等同于 `id`

建议先让页面能优雅缺省，再按 `refactor-guide.md` 补后端展示字段。

## 第一版落地策略

1. 先让 Vue 前端登录、Shell、账号、日志、画廊、设置跑起来。
2. Dashboard 第一版优先接 `/api/dashboard`，必要时再临时聚合 `/health?format=json`、`/api/accounts`、`/api/logs`、`/api/images/storage`。
3. 图片生成页面已恢复入口，但必须走 `/api/image-tasks/*`，不要在浏览器里直接长请求卡住会话。
4. 等页面稳定后再补日志筛选增强。
5. 后端核心 `conversation.py` 暂时只补测试和日志字段，不大拆。

当前落地记录：

- `web-vue` 已完成登录、Shell、Dashboard、账号、日志、画廊、设置和画图的第一版 API adapter；图片任务入口已恢复到主导航。
- 前端已按 `/auth/status.role` 做基础分流：`admin` 进入完整控制台，`user` 只进入画图页；后端管理接口继续要求 `admin`。
- Dashboard 已保留 gemini 原版 6 张模型图表：模型请求分布、调用趋势、成功率趋势、平均响应时间、模型调用占比、模型使用排行；后端已补 `logs.trend` 和 `logs.recent_failures`。
- 2026-06-04 已 smoke Dashboard：图表 canvas 非空、时间范围切换无报错、Header 接口信息可展示聊天/图片模型；“最近失败日志”面板已按当前决策从概览中心移除，失败排查统一进入日志管理页。
- 账号页已改成 chatgpt2api 账号池语义，adapter 做 token 脱敏展示和本地 ID 到 token 的动作映射；统一导入弹窗已接 OAuth、Access Token、Session JSON、Codex JSON、CPA JSON 文件、远程 CPA、Sub2API。
- 账号页已按 `D:\gemini2api\frontend` 参考加入分页和当前页全选；刷新所有账号信息和图片额度使用进度弹窗，前端 20 个一批提交。
- 账号行操作已按原版改成“编辑 + 更多”菜单，更多里保留已有单账号动作。
- 账号编辑弹窗目标是代理模式选择器：全局代理、强制直连、代理组、自定义代理分别保存为空字符串、`direct`、`group:<id>`、原始代理 URL；旧 `profile:<id>` 选择入口已从新控制台移除，只保留历史账号兼容解析和原值保留。
- 2026-06-04 已 smoke 账号页非破坏交互：主表字段、分页、当前页全选、批量菜单、导入模式切换、行菜单和编辑代理入口；控制台无错误，截图见 `artifacts/accounts-smoke-start-20260604.png`、`artifacts/accounts-smoke-menu-edit-20260604.png`、`artifacts/accounts-import-modes-20260604.png`。真实账号导入/刷新/恢复/导出/代理测试仍待确认。
- 日志页现在能从 `/api/logs` 的 `detail` 中展示 `error_code`、`stage`、`reason`、`upstream_message_preview`、`raw_upstream_message` 等诊断字段；status、endpoint、model、account、conversation_id、关键词已改为服务端筛选，并支持 `limit/offset` 分页。
- 日志页调用日志分页已复用 `ListPagination`，按服务端 `total` 和当前 `limit` 计算页数；页面层不再维护私有分页按钮，也不再混用 `hasMore/has_more`。
- 日志页已补时间兜底并对齐旧 `web/src` 主表：时间按 `started_at -> time -> ended_at` 显示，列表展示类型、令牌名称、调用耗时、状态、图片、简述和操作；HTTP、error_code、stage、tool_invoked、上游文本长度等放在详情抽屉；已补当前页勾选和“删除所选”确认弹窗。
- 画廊页现在从 `/api/images` 做服务端分页、统计、搜索、按日期/媒体类型/标签筛选；已接单张/批量删除、批量 zip 下载、复制 URL、标签编辑、过期清理、存储统计、压缩和按目标剩余空间清理；过期判断已统一按 `image_retention_days` 天数计算。
- WebDAV-only 原图响应、缩略图生成和 zip 已有代码级回归覆盖；真实 WebDAV 环境仍需要后续 smoke。
- Vite 本地开发代理已补 `/images` 和 `/image-thumbnails`，本地 `5173` 预览画廊时缩略图会转发到后端。
- 代理页已接全局代理配置、`/api/proxy/test` 和 `/api/proxy/groups*`；新控制台前台账号 `proxy` 目标支持空值、`direct`、`group:<id>` 和自定义 URL。
- 代理引用解析已收口到 `web-vue/src/api/proxy.ts`，账号页和列表显示复用同一套 `parse/serialize/label` helper；旧 `profile:<id>` 作为兼容引用保留，不作为新方案重点。
- 2026-06-04 已 smoke 代理页非破坏交互：主视图、全局代理、分组统计、空状态、新建代理分组弹窗；已补系统接口测试覆盖旧 profile 和多节点代理组创建/列表/删除、profile 引用测试、group 节点轮询和测试写回。真实代理连通性和账号端到端引用仍待确认。
- 2026-06-06 已补后端代理和账号组契约测试：`resolve_proxy` 覆盖显式代理、账号代理、`direct`、`group:<id>`、账号组默认代理组、全局代理、直连和旧 `profile:<id>` 兼容；账号组 API 覆盖缺失代理组失败、重复名称失败和删除账号组清空账号绑定。
- 2026-06-06 已完成后端代理链路复核第一轮：密码重登、Sub2API 远程读取和 Codex 图片 responses 已接入统一代理 session；Codex responses 不再通过 `urllib.request` 绕过账号/账号组/全局代理。注册机代理仍按注册流程独立配置，不归账号代理组调度。
- 2026-06-06 已完成账号页代理模式前台收口：账号编辑不再展示旧 `profile:<id>` 单代理配置，新增/编辑只引导全局代理、强制直连、代理组和自定义代理；已有 `profile:<id>` 老账号按历史兼容引用保留原值。
- 设置页已去掉 Gemini 专有的 daily quota、Nanobanana、音乐/视频字段，改为 chatgpt2api 真实配置：基础连接、图片链路、账号并发、缓存、审核、图片存储和备份。
- 设置页、代理页和图片管理不再手写旧 `basic.*` 字段同步；`web-vue/src/api/settings.ts` 统一生成后端保存 payload，保证 `proxy/base_url/image_retention_days` 和旧兼容字段一致。
- 设置页已补齐图片存储测试/同步、备份测试/立即备份/历史删除、CPA 连接管理、Sub2API 连接管理和 Sub2API 分组读取；账号页远程 CPA/Sub2API 导入现在有对应配置入口。测试/同步/立即备份不做隐式保存，未保存表单会先提示保存。
- 2026-06-06 已完成前端 UI 偏好 adapter 收口：侧边栏、账号分页/视图、日志 limit、图片管理每页数量、公开日志折叠、画图本地对话和本地 task id 都通过 `web-vue/src/lib/preferences.ts` 读写；页面层 `localStorage` 扫描只剩 `api/client.ts` 的登录 token。
- 2026-06-06 已完成图片管理资源 URL helper 收口：`Gallery.vue` 通过 `api/gallery.ts` 的 `resolveGalleryFileUrl` 获取展示、下载和复制链接，不再在页面层拼接资源前缀。
- 2026-06-06 已完成图片管理分页收口：`Gallery.vue` 复用 `ListPagination`，每页数量写入 `preferences.ts` 的 `galleryPageSize`，不再保留页面私有分页按钮和样式。
- 2026-06-06 已跑 `web-vue npm run build` 和只读 R0 smoke：账号、日志、图片管理、设置、文档路由可渲染，应用控制台无错误；未执行真实导入、刷新账号、代理测试、删除、同步存储等有副作用动作。
## 2026-06-05 Closed Gap: Supported Models

- New backend contract: `GET /api/model-catalog`.
- Frontend consumers: Header interface info and `Docs.vue` through `web-vue/src/composables/useModelCatalog.ts`.
- Fallback path: `/v1/models`, then local settings/catalog defaults.
- Validation passed locally after backend restart: the endpoint returned JSON, Header interface info and Docs displayed the same chat/image model catalog, and browser console errors stayed at 0.
- Frontend boundary: page/view components should keep using `web-vue/src/api/*.ts` adapters or composables built on them; the raw `apiClient` is no longer exported from `web-vue/src/api/index.ts`.
