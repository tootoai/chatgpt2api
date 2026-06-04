# API 契约

这份文档面向新前端。目标是让前端只依赖稳定接口和字段，不直接猜后端内部结构。

## 认证

当前管理接口使用 Bearer key：

```http
Authorization: Bearer <admin-or-user-key>
```

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
- `GET /api/image-tasks?ids=...`，仅适合查已知任务。

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
- `profile:<id>`：使用代理管理里的代理分组。

## 图片任务

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
  "size": "1024x1536",
  "quality": "auto"
}
```

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

或 JSON:

```json
{
  "client_task_id": "uuid-from-frontend",
  "prompt": "参考图片生成",
  "model": "gpt-image-2",
  "size": "1024x1536",
  "quality": "auto",
  "image_url": "https://example.com/a.png"
}
```

### 查询任务

```http
GET /api/image-tasks?ids=id1,id2
```

响应：

```json
{
  "items": [
    {
      "id": "...",
      "status": "running",
      "mode": "edit",
      "model": "gpt-image-2",
      "size": "1024x1536",
      "quality": "auto",
      "created_at": "...",
      "updated_at": "...",
      "conversation_id": "...",
      "data": [],
      "error": "",
      "progress": "receiving_image",
      "elapsed_secs": 12,
      "duration_ms": 0
    }
  ],
  "missing_ids": []
}
```

当前任务响应不保证包含 `account_email`、`error_code`、`error_stage`、`can_resume_poll`。这些是建议补强字段，前端第一版要按缺省处理。

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

批量下载请求：

```json
{ "paths": ["2026/06/a.png", "2026/06/b.png"] }
```

返回 `application/zip`。当前后端会优先读取本地文件，本地缺失时通过图片存储服务读取远端内容。

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

代理管理用于维护全局代理和可复用代理分组。实际请求优先级：

```text
显式传入代理 > 账号 proxy > 全局 proxy
```

账号 `proxy=direct` 表示强制直连；账号 `proxy=profile:<id>` 表示引用代理分组。分组不存在或停用时，实际请求会回退到全局代理；测试接口会直接返回 400，提示分组不可用。

### 测试代理

```http
POST /api/proxy/test
```

请求：

```json
{ "url": "http://127.0.0.1:7890" }
```

`url` 可传真实代理 URL，也可传 `profile:<id>`；留空时测试当前全局代理。

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

### 代理分组

```http
GET /api/proxy/profiles
POST /api/proxy/profiles
PUT /api/proxy/profiles
DELETE /api/proxy/profiles/{profile_id}
POST /api/proxy/profiles/test
```

分组字段：

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

`POST /api/proxy/profiles` 可新增或更新单个分组；传 `create_only=true` 时如果分组已存在会返回 400。

`PUT /api/proxy/profiles` 用于整体替换分组列表，谨慎用于导入或批量同步。

`POST /api/proxy/profiles/test` 请求：

```json
{ "id": "hk-1" }
```

或：

```json
{ "url": "http://127.0.0.1:7890" }
```

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
- `proxy_profiles`

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
