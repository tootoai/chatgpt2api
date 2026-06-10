# 数据存储地图

更新时间：2026-06-10

## 当前结论

当前项目不是“所有数据都建表进数据库”的结构。默认 SQLite 只负责账号池和管理 Key；系统设置、代理、账号组、日志、图片、图片标签、外部账号源仍然分别保存在 JSON、JSONL 或文件目录里。

这不是一定错，但要清楚边界：

- 账号量大到 1 万个时，账号池走 SQLite 是对的。
- 概览中心是聚合看板，不应该单独保存一份“概览数据”。
- 图片原文件不应该塞进数据库；数据库最多存图片元数据，原图继续放本地、WebDAV、R2 或对象存储。
- 多容器生产环境不建议多个实例共享同一个 SQLite 文件，后续应迁移 PostgreSQL。

## 总表

| 模块 | 当前保存位置 | 后端入口 | 是否数据库 | 说明 |
| --- | --- | --- | --- | --- |
| 账号池 | `data/accounts.db` 的 `accounts` 表 | `services/storage/database_storage.py`、`services/account_service.py` | 是 | 默认 `STORAGE_BACKEND=sqlite`。每行用 `access_token` 做唯一键，完整账号对象存在 `data` JSON 字段里。 |
| 管理 Key | `data/accounts.db` 的 `auth_keys` 表 | `services/storage/database_storage.py` | 是 | 管理端 key 同样存在 SQLite。 |
| 账号存储后端配置 | 环境变量 `STORAGE_BACKEND`、`DATABASE_URL` | `services/storage/factory.py` | 部分 | 只影响账号和管理 Key。可切 `json/sqlite/postgres/git`。 |
| 系统设置 | 根目录 `config.json` | `services/config.py`、`GET/POST /api/settings` | 否 | base_url、全局代理、图片链路参数、缓存、备份、图片存储、模型配置等都从这里读写。 |
| 账号组 | `config.json` 的 `account_groups` | `services/config.py`、`api/accounts.py` | 否 | 账号组元信息存在配置里；账号自己保存 `group_id`。 |
| 历史代理 profile | `config.json` 的 `proxy_profiles` | `services/config.py`、`api/system.py` | 否 | 后端历史兼容数据，不作为新控制台前台管理方案。 |
| 多节点代理组 | `config.json` 的 `proxy_groups` | `services/config.py`、`api/system.py` | 否 | `group:<id>` 指向一个代理组，组内有多个节点，当前策略是 round-robin。 |
| 全局代理 | `config.json` 的 `proxy`，兼容 `basic.proxy` | `services/config.py`、`services/proxy_service.py` | 否 | 优先级：显式入参代理 > 账号单独代理/direct/custom/group > 账号组默认代理组 > 全局代理 > 直连；旧 `profile:<id>` 仅兼容。 |
| 概览中心 | 不单独保存 | `GET /api/dashboard`、`api/system.py` | 否 | 实时聚合账号统计、调用日志、图片存储统计、配置和存储健康状态。 |
| 调用日志 | `data/logs.jsonl` | `services/log_service.py`、`GET /api/logs` | 否 | 一行一条 JSON。日志页筛选、facets、统计都通过扫描 JSONL 得到。 |
| 运行日志 | 内存 logger + 常见日志文件 | `services/runtime_log_service.py`、`GET /api/runtime-logs` | 否 | 文件来源包括 `CHATGPT2API_RUNTIME_LOG_FILE`、`data/runtime.log`、`data/app.log`、`logs/app.log` 等。 |
| 图片原文件 | `data/images/YYYY/MM/DD/...`，或 WebDAV | `services/image_storage_service.py`、`services/image_service.py` | 否 | 图片是文件，不进数据库。WebDAV 配置在 `config.json.image_storage`；保存入口会校验真实图片 bytes，避免文本或测试假数据伪装成 `.png` 进入图库。 |
| 图片索引 | `data/image_index.json` | `services/image_storage_service.py` | 否 | 保存图片 rel/path、大小、创建时间、本地/WebDAV 状态、远程 URL 等元数据；图库列表会跳过并剔除无效本地图片索引。 |
| 图片缩略图 | `data/image_thumbnails/...` | `services/image_service.py` | 否 | 缩略图按需生成，可清理重建。 |
| 图片标签 | `data/image_tags.json` | `services/image_tags_service.py` | 否 | 以图片路径为 key，保存标签数组。 |
| 图片任务 | `data/image_tasks.json` | `services/image_task_service.py`、`api/image_tasks.py` | 否 | 当前新前端已恢复“画图”入口；任务状态仍存在这个文件里。 |
| CPA 连接 | `data/cpa_config.json` | `services/cpa_service.py`、`api/accounts.py` | 否 | 保存远程 CPA 池配置和导入进度。 |
| Sub2API 连接 | `data/sub2api_config.json` | `services/sub2api_service.py`、`api/accounts.py` | 否 | 保存 Sub2API 服务器配置和导入进度。 |
| 注册机配置 | `data/register.json` | `services/register_service.py` | 否 | 当前新前端第一版暂不接注册机主入口。 |
| 备份状态 | `data/backup_state.json` | `services/config.py`、`services/backup_service.py` | 否 | 保存最近一次备份状态。备份配置本身在 `config.json.backup`。 |
| 前端登录 Key | 浏览器 `localStorage.chatgpt2api.adminKey` | `web-vue/src/api/client.ts` | 否 | 只在当前浏览器生效。换浏览器不会带过去。 |
| 前端页面偏好 | 浏览器 `localStorage` | `web-vue/src/lib/preferences.ts` | 否 | 账号页 page size/视图、日志页 limit、图片管理 page size、侧边栏折叠等都是浏览器偏好；页面层不直接散落存储 key。 |

## 为什么概览中心不建表

概览中心展示的是派生数据：

- 账号总数、正常账号、限流账号、异常账号、禁用账号、剩余额度来自账号池。
- 模型请求分布、调用趋势、成功率趋势、平均响应时间、模型调用占比、模型使用排行来自调用日志。
- 图片数量、占用空间来自图片目录和图片索引。
- 存储健康状态来自当前账号存储后端的 health check。

所以现在的做法是 `GET /api/dashboard` 每次读取当前数据并聚合。后续如果日志量很大导致概览变慢，可以加“聚合表”或“按小时/天 rollup”，但也不建议直接把看板数字当主数据保存。

## 当前这样行不行

短期本地开发和单容器运行可以：

- 1 万账号：SQLite 可以支撑，账号写入已经从整包 JSON 改成增量写 SQLite。
- 日志：JSONL 适合简单追加和排障，但日志量大后筛选会越来越慢。
- 图片：文件目录 + 索引 JSON 能跑，但图片多到几万、跨节点或 WebDAV-only 场景会需要更强的元数据索引。
- 配置：`config.json` 适合单实例；多实例同时写配置会有并发覆盖风险。

## 后续数据库化建议

如果继续走 1000 TPM、多实例、长期运行，建议把“主数据”和“高频查询元数据”迁到 PostgreSQL，而不是继续扩大 SQLite/JSON：

| 优先级 | 建议表 | 原因 |
| --- | --- | --- |
| P0 | `accounts`、`auth_keys` | 已有 SQLite 结构，后续迁 PostgreSQL 最直接。 |
| P1 | `account_groups`、`proxy_groups`、`proxy_nodes` | 这些已经变成管理台核心配置，多实例下不适合继续靠 `config.json`。历史 `proxy_profiles` 仅在旧数据仍使用时做兼容迁移。 |
| P1 | `call_logs` | 日志筛选、模型统计、失败诊断会越来越依赖索引。 |
| P2 | `image_assets`、`image_asset_tags` | 图片原文件仍放对象存储，DB 只保存路径、大小、hash、标签、来源、创建时间。 |
| P2 | `image_tasks`、`import_jobs`、`backup_jobs` | 任务进度适合持久化，方便恢复和跨进程查询。 |
| P3 | `dashboard_rollups` | 当 `call_logs` 很大时，用小时/天聚合表加速概览。 |

## 不建议现在马上全迁

现在前端还在收口，后端图片链路也还没正式拆 Go 数据面。这个阶段直接把所有配置、日志、图片索引全迁数据库，会带来三类风险：

- 迁移风险：旧文件数据要兼容导入，容易把账号、代理、图片标签弄丢。
- 并发风险：如果没有先定义事务边界和锁策略，只是换表，不一定更稳。
- 前端收口被打断：管理台还有 UI 和真实 smoke 没完全闭环。

更稳的路线是：

1. 保持当前存储地图清晰。
2. 账号池继续 SQLite，本地先用。
3. 前端先收口，手动测试发现真实瓶颈。
4. Go POC 或多实例方案确定后，再迁 PostgreSQL，并优先迁账号组、代理组、日志和图片元数据。

## 2026-06-06 smoke 后结论

本轮只读 smoke 没有发现需要立刻迁库才能继续的阻塞点：账号分页 API、日志分页 API、图片分页 API 都能正常返回，前端主要页面也能正常加载。账号、日志、图片管理分页和页面偏好已经统一到前端 adapter/组件层。下一步先继续前端收口和手动 smoke；数据库优化按真实瓶颈推进，不在当前阶段把配置、日志、代理组、图片索引一次性全迁。
