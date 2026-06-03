# 新前端页面规格

这份规格面向 Vue 前端迁移。页面可以复用 `gemini-web2api` 的布局、组件和视觉结构，但数据模型以 chatgpt2api 为准。

## 总体导航

第一版建议保留这些页面：

- 概览中心
- 账号管理
- 图片任务
- 日志中心
- 图片画廊
- 设置中心
- 监控

暂缓：

- 注册机
- 公开日志页
- 公开 uptime 页
- 文档页，可先隐藏或改成本项目接口说明

## 登录页

接口：

- `POST /auth/login`
- 可选 `GET /version`

交互：

- 输入管理员 key 或用户 key。
- 登录成功后保存本地 token。
- 请求头统一使用 `Authorization: Bearer <key>`。

注意：

- 这不是密码登录。
- 不要显示完整 key。

## 概览中心

第一版数据源：

- `GET /health?format=json`
- `GET /api/accounts`
- `GET /api/logs?type=call`
- `GET /api/images/storage`

建议后端补：

- `GET /api/dashboard`

卡片：

- 可用账号数
- 限流账号数
- 异常账号数
- 剩余额度
- 今日图片成功数
- 今日图片失败数
- 平均耗时
- 图片存储占用

图表：

- 账号状态分布
- 图片请求趋势
- 成功率趋势
- 失败原因排行
- 账号失败排行

跳转：

- 点击失败排行进入日志中心并带筛选条件。
- 点击账号状态进入账号管理。

## 账号管理

接口：

- `GET /api/accounts`
- `POST /api/accounts`
- `DELETE /api/accounts`
- `POST /api/accounts/update`
- `POST /api/accounts/refresh`
- `GET /api/accounts/refresh/progress/{progress_id}`
- `POST /api/accounts/re-login`
- `GET /api/accounts/re-login/progress/{progress_id}`
- `POST /api/accounts/oauth/start`
- `POST /api/accounts/oauth/finish`
- `/api/auth/users`

列表字段：

- 邮箱
- 类型
- 来源
- 状态
- 剩余额度
- 成功/失败
- 最近使用时间
- 代理

操作：

- 新增 token 或 OAuth 账号。
- 批量刷新。
- 批量重登。
- 批量删除。
- 单账号编辑状态、quota、proxy。
- 导出账号，必须二次确认。

注意：

- token 默认脱敏。
- 刷新和重登必须展示进度。
- CPA/Sub2API 可以放到折叠区，不作为主流程。

## 图片任务

接口：

- `POST /api/image-tasks/generations`
- `POST /api/image-tasks/edits`
- `GET /api/image-tasks`
- `POST /api/image-tasks/{task_id}/resume-poll`

功能：

- 文生图提交。
- 图生图上传一张或多张参考图。
- 支持 `image_url`，但前端要提示必须是可访问图片 URL。
- 任务列表轮询。
- 任务详情抽屉。
- 成功结果预览和下载。
- 失败后展示原始错误。
- 有 `conversation_id` 且超时类错误时显示继续轮询。

状态映射：

| 后端状态 | 前端显示 |
| --- | --- |
| `queued` | 排队中 |
| `running` | 生成中 |
| `success` | 已完成 |
| `error` | 失败 |

进度映射：

| progress | 前端显示 |
| --- | --- |
| `getting_account` | 正在选择账号 |
| `image_upload_prepare` | 正在准备参考图 |
| `image_upload_registered` | 参考图已登记 |
| `image_upload_complete` | 参考图上传完成 |
| `image_upload_failed` | 参考图上传失败 |
| `image_stream_resolve_start` | 已提交上游，等待结果 |
| `receiving_image` | 正在接收图片 |

## 日志中心

接口：

- `GET /api/logs`
- `POST /api/logs/delete`

筛选：

- 类型
- 状态
- endpoint
- model
- account_email
- conversation_id
- 日期
- 关键词

详情：

- 请求时间
- 耗时
- endpoint
- model
- status
- request_text
- request_shape
- error
- urls
- account_email
- conversation_id

注意：

- 后端当前只支持 type/date 服务端筛选，其他筛选第一版可前端本地做。
- 错误 JSON 要格式化显示。
- 上游文本回复要完整可复制。

## 图片画廊

接口：

- `GET /api/images`
- `POST /api/images/delete`
- `POST /api/images/download`
- `GET /api/images/download/{image_path}`
- `GET /api/images/tags`
- `POST /api/images/tags`
- `DELETE /api/images/tags/{tag}`
- `GET /api/images/storage`

功能：

- 日期筛选。
- 标签筛选。
- 网格预览。
- 大图预览。
- 复制 URL。
- 下载单张/批量下载。
- 删除单张/批量删除。
- 标签编辑。
- 存储统计、压缩、清理入口。

注意：

- 删除必须确认。
- 批量下载和删除要有选中状态。

## 设置中心

接口：

- `GET /api/settings`
- `POST /api/settings`
- `POST /api/proxy/test`
- `POST /api/backup/test`
- `POST /api/image-storage/test`
- `POST /api/image-storage/sync`
- `/api/backups*`

分组：

- 基础代理。
- 图片超时和重试。
- 账号并发。
- 图片并行生成。
- 自动移除异常/限流账号。
- 图片存储。
- 备份。
- 敏感词和审核。
- 用户密钥。

注意：

- 敏感字段不要完整回显。
- 保存前展示即将变更的关键项。

## 监控页

接口：

- `GET /health?format=json`
- `GET /api/storage/info`

展示：

- 服务状态。
- 号池健康。
- 存储后端健康。
- 版本。
- 最近异常摘要。

## 注册机，后续

后续可从 `D:\codexzz\webfree_server` 接成独立任务页：

- 注册任务。
- 任务日志。
- 成果账号导入。
- 验证码/邮箱状态。

第一版不接，原因是它和主控制台风险不同，容易把账号管理和注册自动化耦合在一起。
