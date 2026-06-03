# 重构指南

这份文档不是第一阶段行动清单。当前阶段先完成地图、接口契约和前端适配。后端重构只在必要时小步做。

## 重构原则

- 先补文档，再改接口，再改实现。
- 先新增聚合接口，不动核心链路。
- 先写测试，再动图片链路。
- 每次重构都必须能说明：降低了哪个调用方需要知道的细节。

## 当前不建议立刻重构的模块

### `services/protocol/conversation.py`

原因：

- 图片链路核心，稳定性优先。
- 当前已经包含多种失败兼容逻辑。
- 前端重写不要求立即拆它。

允许的小改：

- 增加结构化错误字段。
- 增加日志事件。
- 给已有逻辑补测试。

不建议的大改：

- 一次性拆成多个 runner。
- 改账号重试语义。
- 改 poll 顺序。

### `services/account_service.py`

原因：

- 账号池、并发槽、刷新、限流都在这里。
- 改错会直接导致“账号明明够但用不了”。

允许的小改：

- 补统计方法。
- 补只读聚合数据。
- 补状态解释。

不建议的大改：

- 改 `get_available_access_token` 选号规则。
- 改并发槽获取和释放顺序。

## 推荐重构候选

### 1. Dashboard 聚合模块

涉及文件：

- `api/system.py`
- `services/account_service.py`
- `services/log_service.py`
- `services/image_service.py`

问题：

- 新前端需要概览图表。
- 如果前端自己聚合多个接口，会重复统计和重复字段转换。

方案：

- 新增只读聚合接口，例如 `GET /api/dashboard`。
- 聚合账号、日志、图片存储。
- 不影响现有接口。

收益：

- 前端接口更小。
- 图表数据稳定。
- 不碰核心图片链路。

### 2. 日志展示模型

涉及文件：

- `services/log_service.py`
- `api/system.py`

问题：

- 当前日志 detail 足够排错，但前端需要统一字段。
- 图片错误、账号错误、普通调用错误混在一起。

方案：

- 增加日志规范化函数。
- 输出统一展示字段：
  - `endpoint`
  - `status`
  - `model`
  - `account_email`
  - `conversation_id`
  - `error_code`
  - `error_message`
  - `duration_ms`
  - `image_urls`

收益：

- 日志页面不用自己猜字段。
- 失败原因统计更准确。

### 3. 图片任务展示模型

涉及文件：

- `services/image_task_service.py`
- `api/image_tasks.py`

问题：

- 新前端要显示任务详情、恢复轮询、进度。
- 任务需要更清楚暴露失败上下文。

方案：

- 保持任务接口不变。
- 增加可选展示字段：
  - `account_email`
  - `conversation_id`
  - `error_code`
  - `error_stage`
  - `can_resume_poll`
- 持久化这些字段，避免服务重启后任务详情丢失关键诊断信息。

收益：

- 图片任务页面能直接判断下一步动作。

### 4. Auth status 小接口

涉及文件：

- `api/system.py`
- `services/auth_service.py`

问题：

- `gemini-web2api` 前端路由守卫已有 `/auth/status` 概念。
- chatgpt2api 当前只有 `POST /auth/login` 和 `GET /version`。

方案：

- 新增只读 `GET /auth/status`。
- Bearer key 有效时返回身份、角色、版本。
- 无效时返回 401。

收益：

- 前端登录态判断更清楚。
- 不需要把 `/version` 当认证探测接口。

### 5. 前端 API adapter

涉及文件：

- 新 Vue 前端 `src/api/*.ts`
- 新 Vue 前端 `src/types/api.ts`

问题：

- gemini-web2api 前端字段和 chatgpt2api 字段不同。

方案：

- 不改页面到处适配。
- 在 API module 里做字段转换。
- 页面只使用 chatgpt2api 类型。

收益：

- 迁移更快。
- 后续后端字段变化影响集中。

### 6. 注册机任务模块，后续

涉及：

- `D:\codexzz\webfree_server`
- 后续可能新增 `services/register_task_service.py`

问题：

- 注册、刷新、检测是脚本式操作。
- 不适合直接嵌入主设置页。

方案：

- 后续做独立任务模块。
- 前端只提交任务、看日志、导入产物。

收益：

- 不影响主控制台稳定性。
- 减少误操作。

## 优先级

1. 新增或整理 Dashboard 聚合数据。
2. 日志展示模型规范化。
3. 图片任务展示字段补强。
4. Auth status 小接口。
5. 前端 API adapter。
6. 注册机任务模块。
7. 图片核心链路重构，最后考虑。

## 重构验收

每个重构必须满足：

- 原有 `/v1/*` 兼容接口不破。
- 原有管理接口不破。
- 有至少一个相关测试。
- 新前端对应页面能工作。
- 日志能解释失败原因。
