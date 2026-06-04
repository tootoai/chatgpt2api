# 前端接口与动作风险地图

更新时间：2026-06-04

这份文档用于约束 `web-vue/` 新控制台。它回答三个问题：

- 每个页面用哪些后端接口。
- 每个按钮是否会修改账号、日志、图片、设置或外部服务。
- 浏览器 smoke 时哪些动作可以直接点，哪些必须等明确确认。

风险等级：

| 等级 | 含义 | smoke 策略 |
| --- | --- | --- |
| R0 只读 | 只读取后端数据或打开本地 UI 状态 | 可以直接验证 |
| R1 本地状态 | 只改前端临时状态，例如筛选、分页、打开弹窗 | 可以直接验证 |
| R2 可恢复写入 | 保存配置、编辑标签、启用/禁用、刷新缓存等 | 需要明确对象；普通编辑保存即确认，批量/状态类动作再弹确认 |
| R3 外部副作用 | 会访问外部 CPA/Sub2API/WebDAV/R2/代理/OAuth | 需要真实配置和明确确认 |
| R4 破坏性 | 删除账号、删除日志、删除图片、清理存储 | 默认禁止 smoke，必须单独确认 |

## 全局规则

- 页面组件不能绕过 `src/api/*.ts` 直接请求后端。
- 只读 smoke 允许打开页面、切换筛选、分页、打开弹窗、查看详情。
- 任何删除、清理、导入、刷新全部账号、恢复异常账号、保存设置、代理测试、WebDAV/R2 测试都不能在未确认时执行。
- 图片任务和本地画图第一版隐藏；后续恢复时必须走 `/api/image-tasks/*`，不能让浏览器直接等长图像请求。

2026-06-04 动作保护落地：

- 账号页：OAuth 登录开始/完成、账号代理测试、远程 CPA 文件列表、Sub2API 账号列表、远程 CPA/Sub2API 导入、账号导出、单账号刷新、单账号启用/禁用已加前置确认；批量刷新、恢复异常、重置、启用/禁用、删除继续使用原有确认。
- 画廊页：保存保留天数、预估按目标清理已加前置确认；删除、过期清理、压缩、执行清理继续使用原有确认。
- 代理页：全局代理保存、全局代理测试、代理分组测试、代理分组启停已加前置确认；删除分组继续使用原有确认。
- 设置页：系统设置总保存、图片存储测试、图片存储同步、备份测试、立即备份和 Sub2API 分组读取已加前置确认；删除备份、删除 CPA/Sub2API 连接继续使用原有确认。
- 普通编辑弹窗保存，例如账号编辑、代理分组编辑、图片标签编辑、CPA/Sub2API 连接编辑，不额外叠加二次确认；它们只能在明确测试对象上做 smoke。
- Smoke 验证可以打开这些弹窗，但不能点击最终确认按钮，除非当轮明确指定测试对象。

## 登录和壳

| 页面/模块 | API | 动作 | 风险 | 状态 |
| --- | --- | --- | --- | --- |
| `Login.vue` | `POST /auth/login` | Bearer key 登录 | R1 | 已接 |
| 路由守卫 | `GET /auth/status` | 检查本地 key 是否有效 | R0 | 已接 |
| Header | `GET /version` | 展示版本 | R0 | 已接 |

验收：

- 可以输入 key 登录。
- 刷新后仍能通过 `/auth/status` 留在控制台。
- 无效 key 应回到登录页或显示认证失败。

## 概览中心

| 页面/模块 | API | 动作 | 风险 | 状态 |
| --- | --- | --- | --- | --- |
| `Dashboard.vue` | `GET /api/dashboard?time_range=...` | 加载账号、存储、日志和模型图表聚合 | R0 | 已接 |
| `useDashboardPage.ts` | `GET /api/dashboard` | 时间范围切换、图表缓存 | R0/R1 | 已接 |

应展示：

- 账号总数、正常账号、限流账号、异常账号、禁用账号、剩余图片额度。
- Header 接口信息：基础端点、SDK 接口、完整接口、聊天模型、图片模型。
- 模型请求分布、调用趋势、成功率趋势、平均响应时间、模型调用占比、模型使用排行。

不展示：

- 最近失败日志面板。
- 图片请求分布这种旧命名。
- Gemini lane、fast/thinking/pro/music/video 额度图。

## 账号管理

| 动作 | API | 风险 | smoke 策略 | 状态 |
| --- | --- | --- | --- | --- |
| 加载账号列表 | `GET /api/accounts` | R0 | 可以直接验证 | 已接 |
| 加载代理分组 | `GET /api/proxy/profiles` | R0 | 可以直接验证 | 已接 |
| 搜索、分页、当前页全选 | 前端状态 | R1 | 可以直接验证 | 已接 |
| 打开导入弹窗、切换导入模式 | 前端状态 | R1 | 可以直接验证 | 已接 |
| 打开编辑弹窗 | 前端状态 | R1 | 可以直接验证 | 已接 |
| 测试账号代理 | `POST /api/proxy/test` 或 `POST /api/proxy/profiles/test` | R3 | 需要确认代理配置 | 已接 |
| 保存账号编辑 | `POST /api/accounts/update` | R2 | 需要明确测试账号，显式保存即确认 | 已接 |
| Access Token 导入 | `POST /api/accounts` | R2 | 需要确认测试 token | 已接 |
| Session/Codex/CPA JSON 文件导入 | `POST /api/accounts` | R2 | 需要确认测试材料 | 已接 |
| OAuth 登录开始/完成 | `POST /api/accounts/oauth/start`、`POST /api/accounts/oauth/finish` | R3 | 需要确认外部账号 | 已接 |
| 远程 CPA 文件列表 | `GET /api/cpa/pools/{id}/files` | R3 | 需要确认 CPA 服务 | 已接 |
| 远程 CPA 导入 | `POST /api/cpa/pools/{id}/import` | R3 | 需要确认导入文件 | 已接 |
| Sub2API 账号列表 | `GET /api/sub2api/servers/{id}/accounts` | R3 | 需要确认 Sub2API 服务 | 已接 |
| Sub2API 导入 | `POST /api/sub2api/servers/{id}/import` | R3 | 需要确认导入账号 | 已接 |
| 刷新账号信息/额度 | `POST /api/accounts/refresh` + progress | R3 | 需要确认账号批次 | 已接 |
| 恢复异常账号 | `POST /api/accounts/re-login` + progress | R3 | 需要确认账号批次 | 已接 |
| 导出账号 | `POST /api/accounts/export` | R2 | 需要确认范围 | 已接 |
| 启用/禁用账号 | `POST /api/accounts/update` | R2 | 需要确认目标账号 | 已接 |
| 重置账号状态 | `POST /api/accounts/update` | R2 | 需要确认目标账号 | 已接 |
| 删除账号 | `DELETE /api/accounts` | R4 | 默认禁止 | 已接 |

账号列表字段：

- TOKEN
- 类型/来源
- 状态
- 账户信息
- 创建时间
- 图片额度
- 恢复时间
- 成功/失败
- 操作

代理值约定：

- 空字符串：使用全局代理。
- `direct`：强制直连。
- `profile:<id>`：使用代理分组。
- 其他 URL：自定义代理。

## 日志管理

| 动作 | API | 风险 | smoke 策略 | 状态 |
| --- | --- | --- | --- | --- |
| 加载调用日志 | `GET /api/logs` | R0 | 可以直接验证 | 已接 |
| 服务端筛选 | `GET /api/logs?status=&endpoint=&model=&account=&conversation_id=&search=` | R0 | 可以直接验证 | 已接 |
| 分页 | `GET /api/logs?limit=&offset=` | R0/R1 | 可以直接验证 | 已接 |
| 加载运行日志 | `GET /api/runtime-logs` | R0 | 可以直接验证 | 已接 |
| 运行日志筛选 | `GET /api/runtime-logs?level=&source=&search=&limit=` | R0/R1 | 可以直接验证 | 已接 |
| 打开详情抽屉 | 前端状态 | R1 | 可以直接验证 | 已接 |
| 查看图片预览 | `/images/*`、`/image-thumbnails/*` 或外部 URL | R0/R3 | 本地 URL 可直接验证，外部 URL 只读 | 已接 |
| 当前页勾选/取消 | 前端状态 | R1 | 可以直接验证 | 已接 |
| 删除单条日志 | `POST /api/logs/delete` | R4 | 默认禁止 | 已接 |
| 删除所选日志 | `POST /api/logs/delete` | R4 | 默认禁止 | 已接 |
| 清空日志 | `POST /api/logs/delete` 或旧 clear 入口 | R4 | 默认禁止 | 已接 |

列表主视图保持轻量：

- 时间
- 类型
- 令牌名称
- 调用耗时
- 状态
- 图片
- 简述
- 操作

详情抽屉展示长字段：

- `request_text`
- `error`
- `error_code`
- `stage`
- `reason`
- `upstream_message_preview`
- `raw_upstream_message`
- `account_email`
- `conversation_id`
- raw JSON

已固定规则：

- 真正运行日志已接 `/api/runtime-logs` 只读接口；它读取内存 logger 和可配置日志文件，不混用 `/api/logs` 的业务调用日志删除逻辑。

## 图片画廊

| 动作 | API | 风险 | smoke 策略 | 状态 |
| --- | --- | --- | --- | --- |
| 加载图片列表 | `GET /api/images` | R0 | 可以直接验证 | 已接 |
| 服务端分页/筛选 | `GET /api/images?media_type=&tag=&search=&limit=&offset=` | R0/R1 | 可以直接验证 | 已接 |
| 加载标签 | `GET /api/images/tags` | R0 | 可以直接验证 | 已接 |
| 加载存储统计 | `GET /api/images/storage` | R0 | 可以直接验证 | 已接 |
| 打开大图预览 | `/images/*` | R0/R3 | 本地可直接验证，远端只读 | 已接 |
| 复制 URL | 浏览器剪贴板 | R1 | 可验证但会改剪贴板 | 已接 |
| 下载单张 | `GET /api/images/download/{path}` 或图片 URL | R1/R3 | 点击下载即确认；外部 URL 只读触发 | 已接 |
| 批量 zip 下载 | `POST /api/images/download` | R2/R3 | 需要先选中范围，点击下载即确认 | 已接 |
| 编辑标签 | `POST /api/images/tags` | R2 | 需要明确测试图片，显式保存即确认 | 已接 |
| 删除标签 | `DELETE /api/images/tags/{tag}` | R2/R4 | 默认不 smoke | 已接 |
| 保存保留天数 | `POST /api/settings` | R2 | 需要确认配置变更 | 已接 |
| 清理过期图片 | `POST /api/images/delete` | R4 | 默认禁止 | 已接 |
| 压缩图片 | `POST /api/images/storage/compress` | R2/R3 | 需要确认 | 已接 |
| 预估按目标清理 | `POST /api/images/storage/cleanup-to-target?dry_run=true` | R2 | 需要确认，虽不删除但会跑后端逻辑 | 已接 |
| 执行按目标清理 | `POST /api/images/storage/cleanup-to-target?dry_run=false` | R4 | 默认禁止 | 已接 |

已固定口径：

- 列表服务端分页，避免大图库一次性拉到浏览器。
- 过期判断按 `image_retention_days` 天数计算。
- `basic.image_expire_hours` 仅作为旧字段兼容。
- WebDAV-only 原图、缩略图和 zip 已有代码级回归覆盖，真实环境 smoke 待确认。

## 代理管理

| 动作 | API | 风险 | smoke 策略 | 状态 |
| --- | --- | --- | --- | --- |
| 加载全局代理设置 | `GET /api/settings` | R0 | 可以直接验证 | 已接 |
| 加载代理分组 | `GET /api/proxy/profiles` | R0 | 可以直接验证 | 已接 |
| 打开新建/编辑弹窗 | 前端状态 | R1 | 可以直接验证 | 已接 |
| 保存全局代理 | `POST /api/settings` | R2 | 需要确认配置变更 | 已接 |
| 测试全局代理 | `POST /api/proxy/test` | R3 | 需要确认代理 | 已接 |
| 新建/编辑代理分组 | `POST /api/proxy/profiles` | R2 | 需要明确测试分组，显式保存即确认 | 已接 |
| 测试代理分组 | `POST /api/proxy/profiles/test` | R3 | 需要确认代理 | 已接 |
| 删除代理分组 | `DELETE /api/proxy/profiles/{id}` | R4 | 默认禁止 | 已接 |

后续端到端验收：

- 账号编辑选择 `profile:<id>` 后发起真实图片请求，确认后端代理解析生效。
- 分组停用、分组不存在、`direct` 强制直连的回退行为。

## 设置中心

| 动作 | API | 风险 | smoke 策略 | 状态 |
| --- | --- | --- | --- | --- |
| 加载配置 | `GET /api/settings` | R0 | 可以直接验证 | 已接 |
| 编辑表单字段 | 前端状态 | R1 | 可以直接验证，不保存 | 已接 |
| 保存设置 | `POST /api/settings` | R2 | 需要确认配置变更 | 已接 |
| 图片存储测试 | `POST /api/image-storage/test` | R3 | 需要确认 WebDAV/R2 配置 | 已接 |
| 图片存储同步 | `POST /api/image-storage/sync` | R3 | 需要确认远端存储 | 已接 |
| 备份测试 | `POST /api/backup/test` | R3 | 需要确认 R2/备份配置 | 已接 |
| 立即备份 | `POST /api/backups/run` | R3 | 需要确认 | 已接 |
| 刷新备份列表 | `GET /api/backups` | R0/R3 | 可以读，取决于远端配置 | 已接 |
| 删除备份 | `POST /api/backups/delete` | R4 | 默认禁止 | 已接 |
| CPA 连接列表 | `GET /api/cpa/pools` | R0 | 可以直接验证 | 已接 |
| CPA 连接新增/编辑 | `POST /api/cpa/pools*` | R2/R3 | 需要明确测试来源，显式保存即确认 | 已接 |
| CPA 连接删除 | `DELETE /api/cpa/pools/{id}` | R4 | 默认禁止 | 已接 |
| Sub2API 连接列表 | `GET /api/sub2api/servers` | R0 | 可以直接验证 | 已接 |
| Sub2API 连接新增/编辑 | `POST /api/sub2api/servers*` | R2/R3 | 需要明确测试来源，显式保存即确认 | 已接 |
| Sub2API 连接删除 | `DELETE /api/sub2api/servers/{id}` | R4 | 默认禁止 | 已接 |
| Sub2API 分组读取 | `GET /api/sub2api/servers/{id}/groups` | R3 | 需要确认服务 | 已接 |

已固定规则：

- 测试 WebDAV、同步图片、测试备份、立即备份不做隐式保存。
- 表单存在未保存改动时，测试类按钮应提示先保存。
- CPA/Sub2API 连接管理只配置来源，真正导入动作在账号管理页完成。

## 监控、公开页和文档页

| 页面 | API | 风险 | 当前决策 |
| --- | --- | --- | --- |
| `Monitor.vue` | `GET /public/uptime` | R0 | 可保留为健康页 |
| `PublicLogs.vue` | 公开日志接口 | R0 | 暂缓，不进主线 |
| `PublicUptime.vue` | 公开 uptime 接口 | R0 | 暂缓，不进主线 |
| `Docs.vue` | 无关键管理动作 | R0 | 可替换成项目接口说明或后续隐藏 |

## 图片任务，暂缓

| 动作 | API | 风险 | 当前决策 |
| --- | --- | --- | --- |
| 查询任务 | `GET /api/image-tasks` | R0 | 文件保留，入口隐藏 |
| 创建文生图任务 | `POST /api/image-tasks/generations` | R3 | 第一版不开放 |
| 创建图生图任务 | `POST /api/image-tasks/edits` | R3 | 第一版不开放 |
| 恢复轮询 | `POST /api/image-tasks/{id}/resume-poll` | R3 | 第一版不开放 |

恢复条件：

- 后端任务事件、错误码、阶段日志和结果图存储已经稳定。
- 页面只展示任务状态，不直接等待长请求。
- 失败能显示真实上游文本、`error_code`、`stage`、账号和 conversation。

## 后续 smoke 顺序

1. R0/R1 全页面只读 smoke：Dashboard、Accounts、Logs、Gallery、Proxy、Settings。
2. R2 小范围写入 smoke：用明确测试对象验证保存设置、账号编辑、标签编辑、代理分组编辑；普通编辑弹窗不额外二次确认，点击保存即视为确认。
3. R3 外部副作用 smoke：OAuth、CPA、Sub2API、WebDAV、R2、代理测试。
4. R4 破坏性 smoke：只在明确测试数据上验证删除账号、删除日志、删除图片、清理图库、删除备份。

当前不做：

- 不刷新全部真实账号。
- 不导入真实账号。
- 不删除真实账号、日志、图片或备份。
- 不执行真实图库清理。
- 不执行 WebDAV/R2/CPA/Sub2API/代理测试，除非当轮明确确认。
