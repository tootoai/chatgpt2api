# 前后端缺口清单

这份清单记录新 Vue 控制台落地前需要处理的接口差异。它分清楚当前已有、建议新增、不能照抄三类，防止迁移时误判。

## 当前已有，前端可以直接接

| 功能 | 接口 | 说明 |
| --- | --- | --- |
| 登录 | `POST /auth/login` | Bearer key 登录，不是账号密码登录。 |
| 版本 | `GET /version` | 返回 `{ "version": "..." }`。 |
| 健康状态 | `GET /health?format=json` | 包含号池统计和存储健康，可作为概览临时数据源。 |
| 账号列表 | `GET /api/accounts` | 返回 `{ items }`。 |
| 账号新增/删除/更新 | `/api/accounts*` | 支持 token、OAuth 账号、刷新、重登。 |
| 用户密钥 | `/api/auth/users` | 管理本服务 user key。 |
| 图片任务 | `/api/image-tasks/*` | 新前端图片生成主入口。 |
| 图片画廊 | `/api/images*` | 列表、删除、下载、标签、存储统计。 |
| 日志 | `/api/logs` | 当前只按 `type/start_date/end_date` 过滤，复杂筛选需前端本地做或后端补。 |
| 设置 | `/api/settings` | 返回完整配置对象。 |
| 代理测试 | `POST /api/proxy/test` | 只有测试接口，没有 `/api/proxy` 读写接口。 |
| 备份 | `/api/backups*` | 可接设置页或备份页。 |

## 建议新增，但不阻塞第一版

| 建议接口 | 用途 | 原因 |
| --- | --- | --- |
| `GET /auth/status` | 登录状态探测 | gemini 前端已有这个概念，新增后路由守卫更干净。 |
| `GET /api/dashboard` | 概览聚合 | 避免 Dashboard 前端并发请求多个接口再重复统计。 |
| `GET /api/runtime-logs` | 运行日志 | 当前 `/api/logs` 是业务调用日志，不等同进程运行日志。 |
| `GET /api/logs` 增强筛选 | 按 status、endpoint、account_email、conversation_id 查询 | 日志量上来后前端本地筛选会慢。 |
| 图片任务诊断字段 | `account_email`、`error_code`、`error_stage`、`can_resume_poll` | 让任务页能直接判断失败原因和下一步动作。 |

## 不能照抄的旧前端接口

当前 `web/src/lib/api.ts` 和 gemini 前端里都有一些不完全匹配 chatgpt2api 后端的接口。新前端不要直接复制。

| 来源 | 接口 | 问题 |
| --- | --- | --- |
| gemini 前端 | `/login` | 它是密码登录；chatgpt2api 是 `POST /auth/login` + Bearer key。 |
| gemini 前端 | `/auth/status` | chatgpt2api 当前没有，可新增或前端临时用 `/version` + 本地 token。 |
| gemini 前端 | `/admin/stats` | chatgpt2api 当前没有，建议改成 `/api/dashboard`。 |
| gemini 前端 | `/admin/accounts` | chatgpt2api 是 `/api/accounts`，字段也不同。 |
| gemini 前端 | `/admin/log` | chatgpt2api 是 `/api/logs`，日志结构不同。 |
| 当前 Next 前端 | `/api/proxy` | 后端当前没有这个读写接口，只有 `/api/proxy/test`。 |

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
2. Dashboard 第一版可以前端聚合 `/health?format=json`、`/api/accounts`、`/api/logs`、`/api/images/storage`。
3. 图片生成页面必须走 `/api/image-tasks/*`。
4. 等页面稳定后再补 `/api/dashboard` 和日志筛选增强。
5. 后端核心 `conversation.py` 暂时只补测试和日志字段，不大拆。
