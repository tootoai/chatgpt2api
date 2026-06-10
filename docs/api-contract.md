# API 契约

## 2026-06-05 Account Mutation Performance Notes

### Paginated Account List

```http
GET /api/accounts?page=1&page_size=20&keyword=&status=all&group_id=all
```

Response:
```json
{
  "items": [],
  "total": 0,
  "all_total": 0,
  "page": 1,
  "page_size": 20
}
```

The Vue account page should use this paginated form. It must not fetch the full account pool just to render one page. Calling `GET /api/accounts` without pagination parameters remains backward-compatible and returns the full `items` list.

### Lightweight Account Update

```http
POST /api/accounts/update
```

Request:
```json
{
  "access_token": "token",
  "type": "free",
  "source_type": "codex",
  "status": "正常",
  "quota": 23,
  "proxy": "",
  "group_id": ""
}
```

Response is compact:
```json
{ "item": {} }
```

It must not return the full account list. The frontend should reload or patch local state explicitly after a mutation.

### Batch Account Update

```http
POST /api/accounts/batch-update
```

Request:
```json
{
  "access_tokens": ["token-a", "token-b"],
  "status": "禁用"
}
```

Response:
```json
{ "updated": 2 }
```

Used by the Vue account page for enable, disable, and reset actions in batches of 20. The endpoint is intentionally compact so 1k-10k account pools do not pay a full-list JSON serialization cost on every batch.

### Batch Account Delete

```http
DELETE /api/accounts
```

Request:
```json
{ "tokens": ["token-a", "token-b"] }
```

Response:
```json
{ "removed": 2 }
```

This endpoint is also intentionally compact and does not return `items`.

### Account Groups

```http
GET /api/account-groups
```

Each account group includes `account_count`, computed by the backend from the in-memory account pool:
```json
{
  "groups": [
    {
      "id": "ms",
      "name": "Microsoft",
      "proxy_group_id": "hk-pool",
      "enabled": true,
      "notes": "",
      "account_count": 128
    }
  ],
  "proxy_groups": []
}
```

The frontend must use this field for account-group dialogs and delete confirmations. It should not infer group counts from the current paginated account page.

```http
POST /api/account-groups
```

Rules:

- `id` is normalized from `id` or `name`.
- `name` must be unique after trimming, whitespace folding, and case-insensitive comparison.
- `proxy_group_id` may be empty, but a non-empty value must reference an existing proxy group.

Common errors:

```json
{ "detail": { "error": "proxy group not found" } }
```

```json
{ "detail": { "error": "account group name already exists" } }
```

```http
DELETE /api/account-groups/{group_id}
```

Deleting an account group does not delete accounts. The backend clears `group_id` on bound accounts and returns the remaining groups with server-side `account_count`.

### Lightweight Account Create And Refresh

`POST /api/accounts`, OAuth finish, CPA import, Sub2API import, the account watcher, and register flows call `refresh_accounts(..., include_items=False)` where possible. Creation responses should only return affected account items, not the full account pool. Background refresh progress should also avoid embedding the full account list in `result.items`.

Account creation/import code paths should also call `add_accounts(..., include_items=False)` or `add_account_items(..., include_items=False)` when the caller does not need the full account list. This avoids serializing 1k-10k accounts after every add/import operation. Legacy service callers still get full `items` by default unless they opt out.

这份文档面向新前端。目标是让前端只依赖稳定接口和字段，不直接猜后端内部结构。

## 认证

当前管理接口使用 Bearer key：

```http
Authorization: Bearer <admin-or-user-key>
```

Bearer key 有三类来源，前端不要混用：

- 管理员 key：`config.json` 的 `auth-key`，也可由 `CHATGPT2API_AUTH_KEY` 覆盖；拥有完整管理权限。
- 普通用户 key：管理员通过 `/api/auth/users` 创建，后端只保存哈希；普通用户登录控制台后只进入图像创作页。
- `config.json.basic.api_key`：旧配置字段，不是当前控制台登录或 OpenAI 兼容接口调用用的密钥。Header 的“接口信息”应展示当前浏览器保存的 Bearer key，而不是这个字段。

当前权限边界：

- `/v1/models`、`/v1/images/generations`、`/v1/images/edits` 接受管理员 key 或普通用户 key。
- `/v1/chat/completions`、`/v1/responses`、`/v1/messages`、`/v1/search`、PPT/PSD/可编辑文件任务和管理接口要求管理员 key。

登录接口：

```http
POST /auth/login
```

请求：

- Header 带 `Authorization`。

响应：

```json
{
  "ok": true,
  "authenticated": true,
  "version": "1.4.6",
  "role": "admin",
  "subject_id": "admin",
  "name": "管理员"
}
```

登录状态：

```http
GET /auth/status
```

有效 Bearer key 返回身份、角色、版本。无效或未传 Bearer key 时不抛 401，而是返回：

```json
{
  "ok": false,
  "authenticated": false,
  "version": "1.4.6"
}
```

普通用户密钥管理：

```http
GET /api/auth/users
POST /api/auth/users
POST /api/auth/users/{key_id}
DELETE /api/auth/users/{key_id}
```

这些接口只允许管理员调用。`POST /api/auth/users` 返回的新密钥明文只展示一次；后续列表只返回 id、名称、角色、启用状态、创建时间和最近使用时间。

## 概览中心

后端不提供 gemini 的 `/admin/stats`，新前端直接接 chatgpt2api 的聚合接口：

```http
GET /api/dashboard?time_range=24h&log_limit=5000
```

聚合接口内部使用的数据源：

- `GET /health?format=json`
- `GET /api/accounts`
- `GET /api/logs`
- `GET /api/images/storage`
- `GET /api/image-tasks?ids=...`，适合查已知任务；不传 `ids` 时返回最近可见任务，并带 `quota_summary` 供图像创作 footer 兜底显示额度。

响应结构：

```json
{
  "status": "ok",
  "healthy": true,
  "version": "1.4.6",
  "accounts": {
    "total": 0,
    "active": 0,
    "limited": 0,
    "disabled": 0,
    "abnormal": 0,
    "total_quota": 0,
    "healthy": true
  },
  "storage": {
    "backend": {},
    "health": {},
    "images": {}
  },
  "logs": {
    "total": 0,
    "success": 0,
    "failed": 0,
    "by_endpoint": {},
    "by_model": {},
    "by_status": {},
    "by_error_code": {},
    "recent_failures": [],
    "trend": {
      "labels": ["09:00", "10:00"],
      "total_requests": [0, 12],
      "success_requests": [0, 10],
      "failed_requests": [0, 1],
      "rate_limited_requests": [0, 1],
      "model_requests": {
        "gpt-image-2": [0, 12]
      },
      "model_ttfb_times": {},
      "model_total_times": {
        "gpt-image-2": [0, 32000]
      }
    }
  }
}
```

参数：

- `time_range` 支持 `24h`、`7d`、`30d`，默认 `24h`。
- `log_limit` 支持 1 到 20000，默认 5000。

Dashboard 前端图表直接消费 `logs.trend`：

- 模型请求分布：`model_requests`
- 调用趋势：`success_requests`、`failed_requests`、`rate_limited_requests`
- 成功率趋势：由 `total_requests` 和失败/限流序列计算
- 平均响应时间：`model_total_times`，值为毫秒，前端可换算成秒
- 模型调用占比 / 模型使用排行：由 `model_requests` 聚合

## 账号管理

### 列表

```http
GET /api/accounts
```

响应：

```json
{
  "items": [
    {
      "access_token": "...",
      "type": "plus",
      "source_type": "oauth_login",
      "status": "正常",
      "quota": 10,
      "image_quota_unknown": false,
      "email": "user@example.com",
      "user_id": "...",
      "success": 0,
      "fail": 0,
      "last_used_at": "2026-06-03T00:00:00",
      "proxy": ""
    }
  ]
}
```

状态枚举：

- `正常`
- `限流`
- `异常`
- `禁用`

### 新增账号

```http
POST /api/accounts
```

请求：

```json
{
  "tokens": ["access-token"],
  "accounts": [
    {
      "access_token": "...",
      "refresh_token": "...",
      "id_token": "...",
      "source_type": "oauth_login"
    }
  ]
}
```

### 删除账号

```http
DELETE /api/accounts
```

请求：

```json
{ "tokens": ["access-token"] }
```

### 刷新账号

```http
POST /api/accounts/refresh
GET /api/accounts/refresh/progress/{progress_id}
```

当前语义是“刷新账号信息和额度”的组合动作：

- 请求体传 `access_tokens` 时刷新指定账号；为空数组时由后端解析为刷新全部账号。
- 后端进入 `account_service.refresh_accounts()`，会读取远端账号信息、状态、套餐/图片额度和恢复时间。
- 如果账号保存了 `refresh_token` 且 access token 需要刷新，会先刷新 access token，并处理 token 轮换别名。
- 它不是单独的“只刷新 AT”接口，也不是单独的“只刷新额度”接口。
- 密码重新登录、恢复异常账号走下面的 `/api/accounts/re-login`。

### 重登账号

```http
POST /api/accounts/re-login
GET /api/accounts/re-login/progress/{progress_id}
```

### 更新账号

```http
POST /api/accounts/update
```

请求：

```json
{
  "access_token": "...",
  "type": "plus",
  "status": "正常",
  "quota": 10,
  "proxy": ""
}
```

账号 `proxy` 字段支持三类值：

- 空字符串：使用全局代理。
- `direct`：强制直连，不使用全局代理。
- `group:<id>`：使用代理组，组内按当前策略选取可用节点。
- `profile:<id>`：历史 profile 兼容值，前台不再作为新方案展示。

## 图片任务

### 模型尺寸与参数边界

图片任务的 `size`、`quality` 会原样记录在任务和日志里，但上游链路不同，语义不同：

- 普通 `gpt-image-2` 走 ChatGPT Web `picture_v2` 图片链路。当前后端会通过 `build_image_prompt()` 把尺寸和质量追加成提示词 hint，稳定规格按前端展示的 `auto/1K` 处理；不要把 2K/4K 当成该链路的强约束工具参数。
- `codex-gpt-image-2`、`plus-codex-gpt-image-2`、`team-codex-gpt-image-2`、`pro-codex-gpt-image-2` 等 Codex 图片模型走 `/backend-api/codex/responses` image tool。这里 `size` 与 `quality` 会作为真实工具参数发送给上游，2K/4K 只在这个链路开放。
- Codex 4K 请求可能出现 HTTP 200 但 SSE 事件里返回 `error.code=server_error`、`response.failed` 且没有图片资产的情况。后端会把这类失败标记为 `error_code=server_error`、`stage=codex_image_tool`，并尽量记录 `upstream_error_type` 和 `upstream_request_id`，供任务详情和日志详情展示。

### 文生图任务

```http
POST /api/image-tasks/generations
```

请求：

```json
{
  "client_task_id": "uuid-from-frontend",
  "prompt": "生成图片",
  "model": "gpt-image-2",
  "n": 2,
  "size": "1024x1536",
  "quality": "auto"
}
```

`n` is optional and defaults to `1`; valid range is `1..4`. The async task response may contain multiple `data[]` image assets when `n > 1`.

### 图生图任务

```http
POST /api/image-tasks/edits
```

请求：

- multipart form:
  - `client_task_id`
  - `prompt`
  - `model`
  - `size`
  - `quality`
  - `image` or `images`

多图说明：

- multipart 可以重复提交多个 `image` 字段，也可以用 `images`/`image[]`/`images[]`。
- `images` 字段可以是 JSON 字符串数组，数组项可为 URL、data URL、base64 或 `{ "image_url": "..." }` 对象。
- JSON 请求优先支持 `images` 数组，也兼容 `image` 和 `image_url`。
- 后端会把所有来源归一成多张图片输入；单张最大 50MB，远程 URL 必须能被后端下载并识别为图片。
- 这里的“多图”指多张参考图输入；一次请求输出多张结果由独立的 `n` 控制，当前画图任务接口支持 `n=1..4`。

或 JSON:

```json
{
  "client_task_id": "uuid-from-frontend",
  "prompt": "参考图片生成",
  "model": "gpt-image-2",
  "n": 2,
  "size": "1024x1536",
  "quality": "auto",
  "images": [
    "https://example.com/a.png",
    { "image_url": "https://example.com/b.png" }
  ]
}
```

`images`/`image`/`image_url` describe reference-image inputs. `n` separately controls output count, defaults to `1`, and accepts `1..4`.

### 查询任务

```http
GET /api/image-tasks?ids=id1,id2
```

不传 `ids` 时返回最近可见任务；传 `ids` 时只查本地历史里已知任务。两种响应都会尽量携带 `quota_summary`，前端可先用它刷新 footer 额度，再按需调用独立额度接口。

响应：

```json
{
  "items": [
    {
      "id": "...",
      "status": "running",
      "mode": "edit",
      "model": "gpt-image-2",
      "n": 2,
      "size": "1024x1536",
      "quality": "auto",
      "created_at": "...",
      "updated_at": "...",
      "conversation_id": "...",
      "data": [],
      "error": "",
      "error_code": "",
      "reason": "",
      "upstream_error_type": "",
      "upstream_request_id": "",
      "progress": "receiving_image",
      "elapsed_secs": 12,
      "duration_ms": 0
    }
  ],
  "missing_ids": [],
  "quota_summary": {
    "total_quota": 112,
    "unlimited_quota_count": 0,
    "active_accounts": 1,
    "limited_accounts": 0,
    "abnormal_accounts": 0,
    "disabled_accounts": 0,
    "available": true
  }
}
```

诊断字段按失败类型尽量补齐。前端必须按缺省处理空字段，但如果存在 `error_code`、`stage`、`reason`、`upstream_error_type`、`upstream_request_id`、`raw_upstream_message`、`upstream_message_preview`，应优先展示这些字段来定位真实卡点。

### 查询图像额度

```http
GET /api/image-tasks/quota
```

响应结构与任务列表里的 `quota_summary` 相同。前端必须把非 JSON、401、404 或旧后端 SPA HTML fallback 当作读取失败处理，不能归一化成 `total_quota=0`；只有接口明确返回 `total_quota: 0` 时才显示真实 `剩余 0 张`。

### 恢复轮询

```http
POST /api/image-tasks/{task_id}/resume-poll
```

请求：

```json
{ "extra_timeout_secs": 30 }
```

限制：

- 任务必须是 `error` 状态。
- 错误信息需要是超时类错误。
- 任务里必须有 `conversation_id`。
- 不是所有失败都能恢复轮询。

## 图片画廊

### 列表

```http
GET /api/images?start_date=2026-06-01&end_date=2026-06-03&media_type=image&tag=角色&search=duck&limit=24&offset=0
```

查询参数：

- `start_date` / `end_date`：按图片日期过滤。
- `media_type`：`all`、`image`、`video`、`music`，默认 `all`。
- `tag`：按标签过滤，`all` 或空值表示不过滤。
- `search`：搜索文件名、路径、创建时间、存储类型和标签。
- `limit` / `offset`：服务端分页；`limit=0` 表示兼容旧行为，返回全部匹配项。

响应包含：

- `items`
- `groups`
- `total`
- `total_size`
- `counts`
- `limit`
- `offset`
- `page`
- `page_size`
- `page_count`
- `has_more`

图片字段：

- `rel`
- `name`
- `date`
- `size`
- `url`
- `thumbnail_url`
- `created_at`
- `width`
- `height`
- `tags`
- `storage`
- `local`
- `webdav`

前端适配层额外计算：

- `expired`
- `expires_in_seconds`
- `retention_days`
- `type`

前端兼容说明：新版后端返回 `total/page_count/counts` 后，`web-vue/src/api/gallery.ts` 直接使用服务端分页结果；如果连接旧后端缺少这些字段，前端才退回本地分页。图片过期判断统一使用 `/api/settings` 的 `image_retention_days`，按天计算；`basic.image_expire_hours` 仅作为旧配置字段兼容，不能再按小时理解。

### 删除

```http
POST /api/images/delete
```

请求：

```json
{
  "paths": ["2026/06/a.png"],
  "start_date": "",
  "end_date": "",
  "all_matching": false
}
```

### 下载

- `POST /api/images/download`
- `GET /api/images/download/{image_path}`

单张下载要求已登录身份，返回附件响应；批量 ZIP 仍要求管理员身份。

批量下载请求：

```json
{ "paths": ["2026/06/a.png", "2026/06/b.png"] }
```

返回 `application/zip`。当前后端会优先读取本地文件，本地缺失时通过图片存储服务读取远端内容。

图片生成任务返回的 `data[]` 会同时包含展示 URL 和本地存储相对路径：

```json
{ "url": "http://127.0.0.1:8000/images/2026/06/a.png", "path": "2026/06/a.png" }
```

前端下载应优先用 `path` 调 `/api/images/download/{image_path}`，不要直接对展示 URL 做 `<a target="_blank">` 跳转。

### 标签

- `GET /api/images/tags`
- `POST /api/images/tags`
- `DELETE /api/images/tags/{tag}`

更新单张图片标签：

```json
{ "path": "2026/06/a.png", "tags": ["角色", "成品"] }
```

### 存储

- `GET /api/images/storage`
- `POST /api/images/storage/compress`
- `POST /api/images/storage/cleanup-to-target`

`cleanup-to-target` 参数：

- `target_free_mb`：目标剩余磁盘空间，默认 500。
- `dry_run`：`true` 时只预估删除数量和释放空间，不真正删除。

## 日志

### 列表

```http
GET /api/logs?type=call&start_date=2026-06-03&end_date=2026-06-03&status=failed&endpoint=/v1/images&model=gpt-image-2&limit=50&offset=0
```

响应：

```json
{
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false,
  "items": [
    {
      "id": "...",
      "time": "...",
      "type": "call",
      "summary": "调用失败",
      "detail": {
        "endpoint": "/v1/images/edits",
        "model": "gpt-image-2",
        "status": "failed",
        "request_text": "...",
        "error": "...",
        "account_email": "...",
        "conversation_id": "..."
      }
    }
  ],
  "facets": {
    "statuses": { "failed": 1 },
    "endpoints": { "/v1/images/edits": 1 },
    "models": { "gpt-image-2": 1 },
    "accounts": { "account@example.com": 1 }
  },
  "stats": {
    "total": 1,
    "success": 0,
    "failed": 1,
    "limited": 0,
    "image": 1,
    "text_reply": 1
  }
}
```

新前端要从 `detail` 里提取诊断字段。

服务端筛选支持：

- `type`
- `start_date`
- `end_date`
- `limit`，1 到 20000，默认 500
- `offset`，默认 0
- `status`：`success`、`failed`、`limited` 或后端原始状态
- `endpoint`：支持子串匹配，例如 `/v1/images`
- `model`
- `account`：匹配 `account_email`、`key_name` 或 `key_id`
- `conversation_id`：支持子串匹配
- `search`：全文搜索 summary 和 detail JSON

`facets` 基于 type/date 基础条件返回可选状态、接口、模型和账号；`stats` 基于完整筛选条件返回统计卡片数据。

### 删除

```http
POST /api/logs/delete
```

请求：

```json
{ "ids": ["log-id"] }
```

## 代理管理

代理管理用于维护全局代理和代理组；后端仍保留历史 profile 兼容接口。实际请求优先级：

```text
显式传入代理 > 账号 proxy/direct/group/自定义 URL > 账号组默认代理组 > 全局 proxy > 直连
```

账号 `proxy=direct` 表示强制直连；账号 `proxy=group:<id>` 表示引用代理组。历史账号可能仍存在 `proxy=profile:<id>`，后端保留兼容解析；前台不再作为新方案展示。账号 proxy 引用不存在或停用时，实际请求会继续尝试账号组默认代理组，再回退到全局代理；测试接口会直接返回 400，提示引用不可用。

### 测试代理

```http
POST /api/proxy/test
```

请求：

```json
{ "url": "http://127.0.0.1:7890" }
```

`url` 可传真实代理 URL，也可传 `group:<id>`；留空时测试当前全局代理。历史 `profile:<id>` 仍由后端兼容解析。

响应：

```json
{
  "result": {
    "ok": true,
    "status": 200,
    "latency_ms": 320,
    "error": null
  }
}
```

### 历史 profile 兼容接口

```http
GET /api/proxy/profiles
POST /api/proxy/profiles
PUT /api/proxy/profiles
DELETE /api/proxy/profiles/{profile_id}
POST /api/proxy/profiles/test
```

历史 profile 字段：

```json
{
  "id": "hk-1",
  "name": "香港代理池",
  "proxy": "http://user:password@host:port",
  "no_proxy": "localhost,127.0.0.1",
  "enabled": true,
  "notes": "可选备注"
}
```

`POST /api/proxy/profiles` 可新增或更新单个 profile；传 `create_only=true` 时如果 profile 已存在会返回 400。

`PUT /api/proxy/profiles` 用于整体替换 profile 列表，谨慎用于导入或批量同步。

`POST /api/proxy/profiles/test` 请求：

```json
{ "id": "hk-1" }
```

或：

```json
{ "url": "http://127.0.0.1:7890" }
```

### 多节点代理组

```http
GET /api/proxy/groups
POST /api/proxy/groups
DELETE /api/proxy/groups/{group_id}
POST /api/proxy/groups/test
```

代理组字段：

```json
{
  "id": "hk-pool",
  "name": "香港代理池",
  "strategy": "round_robin",
  "enabled": true,
  "notes": "可选备注",
  "nodes": [
    {
      "id": "hk-1",
      "name": "节点 1",
      "url": "http://user:password@host:port",
      "enabled": true,
      "last_latency_ms": 320,
      "fail_count": 0,
      "last_error": "",
      "cooldown_until": ""
    }
  ]
}
```

`POST /api/proxy/groups/test` 传 `{ "id": "hk-pool" }` 时会测试组内可用节点并返回 `results`；传 `{ "id": "hk-pool", "node_id": "hk-1" }` 时只测试单个节点。

## 设置

### 获取

```http
GET /api/settings
```

响应：

```json
{ "config": {} }
```

### 保存

```http
POST /api/settings
```

请求为完整或部分配置对象。

关键配置：

- `proxy`
- `base_url`
- `image_poll_timeout_secs`
- `image_poll_interval_secs`
- `image_poll_initial_wait_secs`
- `image_account_concurrency`
- `image_parallel_generation`
- `image_settle_enabled`
- `image_check_before_hit_enabled`
- `image_settle_secs`
- `image_timeout_retry_secs`
- `auto_remove_invalid_accounts`
- `auto_remove_rate_limited_accounts`
- `auto_relogin_after_refresh`
- `image_storage`
- `backup`
- `chat_completion_cache`
- `global_system_prompt`
- `sensitive_words`
- `account_groups`
- `proxy_groups`
- `proxy_profiles` (backend compatibility only; not the new control-panel main path)

## 错误格式

常见格式：

```json
{ "detail": { "error": "message" } }
```

或 OpenAI 风格：

```json
{
  "error": {
    "message": "message",
    "type": "server_error",
    "code": "upstream_text_reply"
  }
}
```

前端错误提取顺序：

1. `detail.error`
2. `error.message`
3. `error`
4. `message`
5. HTTP 状态码兜底
## 2026-06-05 Management Model Catalog

```http
GET /api/model-catalog
```

This is the control-panel model contract. It is read-only, admin-authenticated, and does not call upstream OpenAI/ChatGPT. The OpenAI-compatible `GET /v1/models` endpoint remains available for API clients, but the Vue control panel should prefer `/api/model-catalog` so Header and Docs use the same model list.

Response:
```json
{
  "object": "model_catalog",
  "chat_models": ["auto", "gpt-5", "gpt-5-mini"],
  "image_models": ["gpt-image-2", "codex-gpt-image-2"],
  "all_models": ["auto", "gpt-5", "gpt-5-mini", "gpt-image-2", "codex-gpt-image-2"],
  "source": {
    "chat": "config",
    "image": "accounts"
  },
  "openai_models_endpoint": "/v1/models"
}
```

Source rules:
- Chat models come from `model_catalog.chat_models`, then combined catalog chat lists, then fallback defaults.
- Image models come from `image_generation.model_options`, `model_catalog.image_api_models`, `image_generation.supported_models`, then the current account pool, then fallback defaults.
- A Codex Plus/Team/Pro account enables `codex-gpt-image-2` and the matching prefixed model such as `team-codex-gpt-image-2`.
- Frontend fallback order is `/api/model-catalog`, then `/v1/models`, then local settings/catalog fallback.
