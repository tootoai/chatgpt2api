# 新前端重写计划

## 目标

使用本地 `gemini-web2api` Vue 前端作为新控制台基底，重写 API 适配层和页面字段，服务 chatgpt2api 的账号池、图片任务、日志、画廊、设置管理。

## 第一阶段：准备

产物：

- 文档完成：
  - `development-principles.md`
  - `backend-map.md`
  - `image-pipeline.md`
  - `api-contract.md`
  - `frontend-adapter-map.md`
  - `frontend-page-spec.md`
  - `backend-frontend-gap.md`
- 确认前端基底目录：
  - `D:\gemini-web2api-2\gemini-web2api-main\frontend`

验收：

- 明确哪些页面保留、哪些字段删除、哪些接口改接。
- 不修改后端核心图片链路。
- 明确哪些字段当前不存在，只能作为后端补强项。

## 第二阶段：前端骨架迁移

任务：

- 把 Vue 前端先放到临时目录验证，确认 build 和接口适配后再替换正式 `web`。
- 保留：
  - AppShell
  - Router
  - Pinia auth store
  - Toast/Confirm composables
  - ChartCard/StatCard 视觉结构
  - Gallery/Logs/Accounts/Dashboard 页面框架
- 删除或隐藏 Gemini 专有：
  - lane
  - snlm0e
  - cookie resolve
  - pro/thinking/fast 模型配额
  - public display
  - password login

验收：

- `npm run build` 通过。
- 登录页和 Shell 能打开。

## 第三阶段：API 适配

任务：

- 重写 `src/api/client.ts`
  - 使用 Bearer key。
  - 错误提取兼容 `detail.error` 和 OpenAI error。
- 重写 `src/types/api.ts`
  - 定义 chatgpt2api 的 Account、ImageTask、SystemLog、ManagedImage、Settings。
- 重写：
  - `src/api/auth.ts`
  - `src/api/stats.ts`
  - `src/api/reverseAccounts.ts`，可改名 `accounts.ts`
  - `src/api/logs.ts`
  - `src/api/gallery.ts`
  - `src/api/settings.ts`
  - 新增 `src/api/imageTasks.ts`

验收：

- 每个 API module 有明确类型。
- 页面不直接拼后端字段。
- 所有后端不存在的 gemini 接口都已删除或改接。

## 第四阶段：概览中心

页面：`Dashboard.vue`

数据源：

- 优先新增 `GET /api/dashboard`。
- 临时也可前端聚合：
  - `/health?format=json`
  - `/api/accounts`
  - `/api/logs`
  - `/api/images/storage`

图表：

- 账号状态分布。
- 图片请求趋势。
- 成功率趋势。
- 失败原因排行。
- 平均耗时。
- 存储占用。

验收：

- 图表非空。
- 没有账号时有空状态。
- 失败日志能跳转到日志详情。

## 第五阶段：账号管理

页面：`Accounts.vue`

功能：

- 列表。
- 搜索邮箱、状态、来源。
- 批量刷新。
- 批量删除。
- 单账号编辑状态、quota、proxy。
- OAuth 登录入口。
- CPA/Sub2API 导入可以保留成折叠区。

验收：

- 状态颜色明确。
- token 脱敏。
- 刷新/重登进度可见。

## 第六阶段：日志中心

页面：`Logs.vue`

功能：

- 调用日志列表。
- 按类型、状态、endpoint、时间、账号邮箱、conversation id 筛选。
- 图片失败详情抽屉。
- 错误 JSON 格式化。
- 支持复制 conversation_id、account_email、error。

验收：

- 图生图失败能看到具体失败文本。
- 上游文本回复类错误能被识别。
- 日志能反查账号和图片任务。

## 第七阶段：图片任务

新增页面：`ImageTasks.vue`

功能：

- 创建文生图任务。
- 创建图生图任务。
- 任务队列。
- 任务详情。
- 失败后 resume-poll。
- 结果图片预览。

验收：

- 浏览器不被长请求卡住。
- 任务失败不影响继续提交。
- 有 conversation_id 的失败任务可继续轮询。
- 没有诊断字段时页面也能正常显示兜底信息。

## 第八阶段：图片画廊

页面：`Gallery.vue`

功能：

- 日期筛选。
- 标签筛选。
- 图片预览。
- 下载。
- 删除。
- 批量删除。
- 存储统计。
- 压缩和清理入口。

验收：

- 图片 URL 和缩略图正常。
- 删除前确认。
- 批量操作后刷新列表。

## 第九阶段：设置中心

页面：`Settings.vue`

重点设置：

- 代理。
- 图片超时。
- 图片账号并发。
- 图片并行生成。
- 失败重试。
- 自动移除异常/限流账号。
- 图片存储。
- 备份。
- 用户 key。

验收：

- 保存后能显示新配置。
- 敏感字段不明文回显，或有明确脱敏策略。

## 第十阶段：注册机，暂缓

注册机使用：

```text
D:\codexzz\webfree_server
```

第一版不接入主前端。后续可作为任务模块：

- 注册任务。
- 刷新任务。
- 检测任务。
- 任务日志。
- 产物导入账号池。

原因：

- 注册涉及邮箱凭据、网络请求、验证码、脚本运行。
- 和主控制台稳定性风险不同。
- 应当独立任务化，避免误点。
