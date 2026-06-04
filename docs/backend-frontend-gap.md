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
| 图片任务 | `/api/image-tasks/*` | 接口已存在，但第一版 Vue 控制台暂时隐藏图片任务/本地画图入口。 |
| 图片画廊 | `/api/images*` | 列表、删除、下载、标签、存储统计、压缩和按目标剩余空间清理。 |
| 日志 | `/api/logs` | 支持 type/date/status/endpoint/model/account/conversation/search 服务端筛选，并返回分页、facets 和 stats。 |
| 设置 | `/api/settings` | 返回完整配置对象。 |
| 代理管理 | `/api/proxy/test`、`/api/proxy/profiles*` | 支持全局代理测试、代理分组 CRUD、`profile:<id>` 账号引用和 `direct` 强制直连。 |
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
| 当前 Next 前端 | `/api/proxy` | 不照抄旧的虚拟读写接口；新 Vue 前端使用 `/api/settings` 保存全局代理，并使用 `/api/proxy/profiles*` 管理代理分组。 |

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
3. 图片生成页面暂时不进入第一版导航；后续恢复时必须走 `/api/image-tasks/*`，不要在浏览器里直接长请求卡住会话。
4. 等页面稳定后再补日志筛选增强。
5. 后端核心 `conversation.py` 暂时只补测试和日志字段，不大拆。

当前落地记录：

- `web-vue` 已完成登录、Shell、Dashboard、账号、日志、画廊、设置的第一版 API adapter；图片任务 adapter 保留但入口暂时隐藏。
- Dashboard 已保留 gemini 原版 6 张模型图表：模型请求分布、调用趋势、成功率趋势、平均响应时间、模型调用占比、模型使用排行；后端已补 `logs.trend` 和 `logs.recent_failures`。
- 2026-06-04 已 smoke Dashboard：图表 canvas 非空、时间范围切换无报错、Header 接口信息可展示聊天/图片模型；“最近失败日志”面板已按当前决策从概览中心移除，失败排查统一进入日志管理页。
- 账号页已改成 chatgpt2api 账号池语义，adapter 做 token 脱敏展示和本地 ID 到 token 的动作映射；统一导入弹窗已接 OAuth、Access Token、Session JSON、Codex JSON、CPA JSON 文件、远程 CPA、Sub2API。
- 账号页已按 `D:\gemini2api\frontend` 参考加入分页和当前页全选；刷新所有账号信息和图片额度使用进度弹窗，前端 20 个一批提交。
- 账号行操作已按原版改成“编辑 + 更多”菜单，更多里保留已有单账号动作。
- 账号编辑弹窗已接入代理模式选择器，前端把全局代理、强制直连、代理分组、自定义代理分别保存为空字符串、`direct`、`profile:<id>`、原始代理 URL。
- 2026-06-04 已 smoke 账号页非破坏交互：主表字段、分页、当前页全选、批量菜单、导入模式切换、行菜单和编辑代理入口；控制台无错误，截图见 `artifacts/accounts-smoke-start-20260604.png`、`artifacts/accounts-smoke-menu-edit-20260604.png`、`artifacts/accounts-import-modes-20260604.png`。真实账号导入/刷新/恢复/导出/代理测试仍待确认。
- 日志页现在能从 `/api/logs` 的 `detail` 中展示 `error_code`、`stage`、`reason`、`upstream_message_preview`、`raw_upstream_message` 等诊断字段；status、endpoint、model、account、conversation_id、关键词已改为服务端筛选，并支持 `limit/offset` 分页。
- 日志页已补时间兜底并对齐旧 `web/src` 主表：时间按 `started_at -> time -> ended_at` 显示，列表展示类型、令牌名称、调用耗时、状态、图片、简述和操作；HTTP、error_code、stage、tool_invoked、上游文本长度等放在详情抽屉；已补当前页勾选和“删除所选”确认弹窗。
- 画廊页现在从 `/api/images` 做服务端分页、统计、搜索、按日期/媒体类型/标签筛选；已接单张/批量删除、批量 zip 下载、复制 URL、标签编辑、过期清理、存储统计、压缩和按目标剩余空间清理；过期判断已统一按 `image_retention_days` 天数计算。
- WebDAV-only 原图响应、缩略图生成和 zip 已有代码级回归覆盖；真实 WebDAV 环境仍需要后续 smoke。
- Vite 本地开发代理已补 `/images` 和 `/image-thumbnails`，本地 `5173` 预览画廊时缩略图会转发到后端。
- 代理页已接全局代理配置、`/api/proxy/test` 和 `/api/proxy/profiles*`；账号 `proxy` 支持空值、`direct`、`profile:<id>` 三种语义。
- 2026-06-04 已 smoke 代理页非破坏交互：主视图、全局代理、分组统计、空状态、新建代理分组弹窗；已补系统接口测试覆盖代理分组创建/列表/删除和 profile 引用测试。真实代理连通性和账号端到端引用仍待确认。
- 设置页已去掉 Gemini 专有的 daily quota、Nanobanana、音乐/视频字段，改为 chatgpt2api 真实配置：基础连接、图片链路、账号并发、缓存、审核、图片存储和备份。
- 设置页已补齐图片存储测试/同步、备份测试/立即备份/历史删除、CPA 连接管理、Sub2API 连接管理和 Sub2API 分组读取；账号页远程 CPA/Sub2API 导入现在有对应配置入口。测试/同步/立即备份不做隐式保存，未保存表单会先提示保存。
