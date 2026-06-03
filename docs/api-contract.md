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
  "version": "1.4.6",
  "role": "admin",
  "subject_id": "admin",
  "name": "管理员"
}
```

## 概览中心

现有后端暂时没有专门的 `/admin/stats` 聚合接口。新前端第一版有两种方式：

1. 前端聚合多个接口。
2. 后端补一个 `/api/dashboard` 聚合接口。

建议补后端聚合接口，避免前端重复统计。

可用数据源：

- `GET /health?format=json`
- `GET /api/accounts`
- `GET /api/logs`
- `GET /api/images/storage`
- `GET /api/image-tasks?ids=...`，仅适合查已知任务。

建议聚合响应：

```json
{
  "accounts": {
    "total": 0,
    "active": 0,
    "limited": 0,
    "disabled": 0,
    "abnormal": 0,
    "total_quota": 0
  },
  "images": {
    "success": 0,
    "failed": 0,
    "avg_duration_ms": 0,
    "recent_failures": []
  },
  "storage": {
    "total_images": 0,
    "total_size": 0,
    "free_mb": 0
  }
}
```

注意：这是建议新增接口，不是当前已有接口。第一版 Vue 前端如果先不改后端，可以前端聚合现有接口。

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
GET /api/images?start_date=2026-06-01&end_date=2026-06-03
```

响应包含：

- `items`
- `groups`

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

### 标签

- `GET /api/images/tags`
- `POST /api/images/tags`
- `DELETE /api/images/tags/{tag}`

### 存储

- `GET /api/images/storage`
- `POST /api/images/storage/compress`
- `POST /api/images/storage/cleanup-to-target`

## 日志

### 列表

```http
GET /api/logs?type=call&start_date=2026-06-03&end_date=2026-06-03
```

响应：

```json
{
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
  ]
}
```

新前端要从 `detail` 里提取诊断字段。

当前服务端筛选只保证支持：

- `type`
- `start_date`
- `end_date`

`endpoint`、`status`、`account_email`、`conversation_id` 第一版可以前端本地筛选；日志量变大后建议补服务端筛选。

### 删除

```http
POST /api/logs/delete
```

请求：

```json
{ "ids": ["log-id"] }
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
- `image_poll_timeout_secs`
- `image_account_concurrency`
- `image_parallel_generation`
- `image_settle_enabled`
- `image_timeout_retry_secs`
- `auto_remove_invalid_accounts`
- `auto_remove_rate_limited_accounts`
- `image_storage`
- `backup`

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
