# 新前端页面规格

这份规格面向 Vue 前端迁移。页面可以复用 `gemini-web2api` 的布局、组件和视觉结构，但数据模型以 chatgpt2api 为准。

## 总体导航

第一版建议保留这些页面：

- 概览中心
- 账号管理
- 日志中心
- 图片画廊
- 代理管理
- 设置中心
- 监控

暂缓：

- 图片任务，本地画图入口第一版不进导航
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

- `GET /api/dashboard`

卡片：

- 账号总数
- 正常账号数
- 异常账号数
- 限流账号数
- 禁用账号数
- 剩余图片额度

Header：

- 接口地址
- 当前版本
- 系统可用模型
- 存储健康状态

图表：

- 模型请求分布
- 调用趋势
- 成功率趋势
- 平均响应时间
- 模型调用占比
- 模型使用排行

跳转：

- 点击失败日志进入日志中心并带筛选条件。
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

- TOKEN
- 类型 / 来源
- 状态
- 账户信息
- 创建时间
- 图片额度
- 恢复时间
- 成功/失败
- 操作

操作：

- 新增 token 或 OAuth 账号。
- 批量刷新。
- 批量恢复异常账号，调用 `/api/accounts/re-login` 并轮询进度。
- 批量删除。
- 单账号编辑状态、quota、proxy，并支持测试当前代理。
- 导出账号：优先导出完整 OAuth/Codex 认证 JSON；后端没有完整认证材料时回退成旧版每行一个 access token 的 TXT。

注意：

- token 默认脱敏。
- 刷新和重登必须展示进度。
- CPA/Sub2API 可以放到折叠区，不作为主流程。
- chatgpt2api 当前只展示图片额度，不照搬 gemini 的 fast/thinking/pro/music/video 悬浮配额详情。
- 账号编辑里的 proxy 不直接暴露成单个裸输入框，应使用模式选择：使用全局代理、强制直连、代理分组、自定义代理。
- proxy 保存值约定：空字符串表示使用全局代理，`direct` 表示强制直连，`profile:<id>` 表示使用代理管理里的分组，自定义代理保存原始代理 URL。

## 图片任务

第一版暂缓，不进导航，也不作为本地画图入口。

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
- 展示时间优先级：`detail.started_at` -> `time` -> `detail.ended_at`
- 耗时
- status_code
- endpoint
- model
- status
- request_text
- request_shape
- error
- urls
- 结果图片预览
- account_email
- conversation_id
- error_code
- stage
- request_shape
- tool_invoked
- upstream_message_len

注意：

- 日志列表应使用服务端筛选和分页，避免把大日志文件一次性拉到浏览器里本地过滤。
- 日志表格主视图对齐旧 `web/src`：时间、类型、令牌名称、调用耗时、状态、图片、简述、操作；不要把长 request_text/error 直接塞进列表。
- 后端支持 `type`、日期、`status`、`endpoint`、`model`、`account`、`conversation_id`、`search`、`limit`、`offset`。
- 后端返回 `total`、`has_more`、`facets` 和 `stats`，前端筛选选项和统计卡片优先使用这些字段。
- 错误 JSON 要格式化显示。
- 上游文本回复要完整可复制。
- `detail.urls` 中的 `/images`、`/image-thumbnails` 和外部 http(s) 图片链接要在列表和详情里显示预览；加载失败时显示“无法预览”占位。
- 失败诊断字段放在详情抽屉里展示，列表只显示简述，避免宽表读起来太乱。

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
- `POST /api/images/storage/compress`
- `POST /api/images/storage/cleanup-to-target`

功能：

- 服务端分页、搜索、日期筛选、媒体类型筛选和标签筛选，避免大图库一次性拉到浏览器里本地过滤。
- 日期筛选。
- 标签筛选。
- 网格预览。
- 大图预览。
- 复制 URL。
- 下载单张/批量下载。
- 删除单张/批量删除。
- 标签编辑。
- 存储统计、压缩、清理入口。
- 图片保留天数设置和过期清理，口径对齐后端 `image_retention_days`，按天计算。

注意：

- 删除必须确认。
- 批量下载和删除要有选中状态。
- 本地开发要代理 `/images` 和 `/image-thumbnails`，否则缩略图会请求到 Vite 自身。
- 小于 128B 或加载失败的文件按坏图处理，显示“无法预览”占位，不阻塞画廊操作。

## 设置中心

接口：

- `GET /api/settings`
- `POST /api/settings`
- `POST /api/proxy/test`
- `POST /api/backup/test`
- `POST /api/image-storage/test`
- `POST /api/image-storage/sync`
- `/api/backups*`
- `/api/cpa/pools*`
- `/api/sub2api/servers*`

分组：

- 基础连接。
- 图片超时和重试。
- 账号并发。
- 图片并行生成。
- 自动移除异常/限流账号。
- 聊天补全缓存。
- 图片存储。
- 备份。
- CPA 连接管理。
- Sub2API 连接管理。
- 敏感词和审核。
- 用户密钥。

注意：

- 敏感字段不要完整回显。
- 保存前展示即将变更的关键项。
- 不显示 Gemini/Nanobanana/pro/music/video 这些非本项目配置。
- 测试 WebDAV 和测试备份前应保存当前设置，否则后端会测到旧配置。
- CPA/Sub2API 连接管理只负责配置来源；具体导入动作仍放在账号管理页。

## 代理管理

接口：

- `GET /api/settings`
- `POST /api/settings`
- `POST /api/proxy/test`
- `GET /api/proxy/profiles`
- `POST /api/proxy/profiles`
- `PUT /api/proxy/profiles`
- `DELETE /api/proxy/profiles/{profile_id}`
- `POST /api/proxy/profiles/test`

功能：

- 编辑全局代理。
- 测试全局代理。
- 新建、编辑、启用/停用、删除代理分组。
- 测试单个分组。
- 复制 `profile:<id>` 账号引用。
- 分组列表搜索和分页。

注意：

- 账号代理优先级为：账号代理 > 代理分组 > 全局代理。
- 账号填写 `direct` 时强制直连。
- 分组密码在列表里脱敏显示。

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
