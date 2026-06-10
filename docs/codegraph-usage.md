# codegraph 使用说明

`codegraph` 已在本项目跑过索引。它不是自动报告生成器，而是代码结构查询工具：先建索引，再用 query/callers/callees/impact 查符号、调用方、被调用方和影响面。

## MCP 状态

- 本机已安装 `@colbymchenry/codegraph`，命令为 `codegraph`。
- CodeGraph 本身支持 MCP：`codegraph serve` 可以启动 MCP server，`codegraph install` 可以安装到 Codex CLI、Claude Code、Cursor、opencode、Hermes Agent 等环境。
- 当前 Codex Desktop 会话没有暴露 CodeGraph MCP tool；`tool_search` 没有发现可直接调用的 CodeGraph MCP 工具。
- 当前工作流先使用 CLI；如果要长期用 MCP，需要安装到对应 agent 配置后重启会话。

## 当前索引状态

最近一次核对：

```text
Project: D:\chatgpt2api
Files: 361
Nodes: 6,555
Edges: 13,500
Routes: 100
Backend: node:sqlite - built-in (full WAL)
```

2026-06-06 已执行 `codegraph sync D:\chatgpt2api`，最终 `codegraph status` 显示索引 up to date。最近一次结构同步提示：`Synced 1 changed files`，修改 1 个文件、更新 1 个节点。

2026-06-10 已再次执行 `codegraph sync D:\chatgpt2api` 和 `codegraph status D:\chatgpt2api`。本次同步提示 `Synced 15 changed files`，最终状态为 up to date；当前索引统计为 Files 400、Nodes 7,095、Edges 14,549、Routes 101。

## 常用命令

```powershell
codegraph status D:\chatgpt2api
codegraph query "ImageTask" --path D:\chatgpt2api
codegraph query "accountsApi" --path D:\chatgpt2api
codegraph query "get_available_access_token" --path D:\chatgpt2api
codegraph query "release_image_slot" --path D:\chatgpt2api
codegraph query "LoggedCall" --path D:\chatgpt2api
codegraph callees "exportAccounts" --path D:\chatgpt2api
```

如果要看某个符号谁调用它：

```powershell
codegraph callers "get_available_access_token" --path D:\chatgpt2api
```

如果要看改某个符号可能影响哪里：

```powershell
codegraph impact "get_available_access_token" --path D:\chatgpt2api
```

## 本项目优先查询点

### 前端账号页

```powershell
codegraph query "exportAccounts" --path D:\chatgpt2api
codegraph callers "exportAccounts" --path D:\chatgpt2api
codegraph callees "exportAccounts" --path D:\chatgpt2api
codegraph impact "exportAccounts" --path D:\chatgpt2api
codegraph impact "loadCPAFiles" --path D:\chatgpt2api
codegraph impact "loadSub2APIAccounts" --path D:\chatgpt2api
codegraph impact "export_accounts" --path D:\chatgpt2api
```

2026-06-05 结论：

- 账号主 adapter 已从 `reverseAccounts.ts` 收口为 `web-vue/src/api/accounts.ts`。
- `reverseAccounts.ts` 只保留 re-export 兼容入口，新代码应使用 `accountsApi`。
- `exportAccounts` 有两层：页面逻辑函数 `web-vue/src/views/accounts/useAccountsPage.ts` 和 API adapter 函数 `web-vue/src/api/accounts.ts`。
- 页面层入口在 `web-vue/src/views/Accounts.vue` 模板和 `useAccountsPage.ts` 返回值中，Vue template 事件仍需配合 `rg` 检查。
- 后端出口是 `api/accounts.py` 的 `POST /api/accounts/export`。
- `loadCPAFiles`、`loadSub2APIAccounts` 影响范围集中在 `useAccountsPage.ts`。
- CodeGraph 没有完整识别 Vue template 里的 `@click="loadCPAFiles"`、`@click="loadSub2APIAccounts"` 调用，Vue 模板入口必须继续配合 `rg` 检查。

更完整的控制台前后端地图见 `docs/control-panel-code-map.md`。

### 图片链路

```powershell
codegraph query "stream_image_outputs_with_pool" --path D:\chatgpt2api
codegraph query "ImageContentPolicyError" --path D:\chatgpt2api
codegraph query "upstream_text_reply" --path D:\chatgpt2api
codegraph query "_poll_image_results" --path D:\chatgpt2api
```

目的：

- 找图生图失败在哪里被识别。
- 找文本回复伪工具参数在哪里被转成错误。
- 找 poll 超时和恢复轮询逻辑。

### 账号池

```powershell
codegraph query "get_available_access_token" --path D:\chatgpt2api
codegraph query "release_image_slot" --path D:\chatgpt2api
codegraph query "mark_image_result" --path D:\chatgpt2api
```

目的：

- 确认并发槽获取和释放。
- 判断“账号明明够但不可用”是选号、状态、额度还是释放问题。

### 日志

```powershell
codegraph query "LoggedCall" --path D:\chatgpt2api
codegraph query "log_service.add" --path D:\chatgpt2api
```

目的：

- 查失败详情是否写入日志。
- 查 `account_email`、`conversation_id`、`error` 是否在链路里丢失。
- 前端日志页的后端字段解析已收口到 `web-vue/src/api/logs.ts`：`SystemLogRow`、`normalizeSystemLogRow`、`isSystemLogFailed`、`isSystemLogSuccess`、`isSystemLogLimited`。

本轮可查：

```powershell
codegraph query "SystemLogRow" --path D:\chatgpt2api
codegraph query "normalizeSystemLogRow" --path D:\chatgpt2api
```

### 前端接口

```powershell
codegraph query "fetchImageTasks" --path D:\chatgpt2api
codegraph query "fetchSystemLogs" --path D:\chatgpt2api
codegraph query "fetchProxy" --path D:\chatgpt2api
```

目的：

- 查当前前端有没有调用后端不存在的接口。
- 查新 Vue 前端迁移时哪些函数可以复用，哪些必须重写。

### 前端账号状态

```powershell
codegraph query "AccountBackendStatus" --path D:\chatgpt2api
codegraph query "normalizeAccountBackendStatus" --path D:\chatgpt2api
```

目的：

- 确认 `正常/限流/异常/禁用` 的合法值只由 `web-vue/src/api/accounts.ts` 管理。
- 避免账号页继续散落后端状态常量。

### 前端设置和代理引用

```powershell
codegraph query "prepareSettingsForSave" --path D:\chatgpt2api
codegraph query "parseProxyReference" --path D:\chatgpt2api
codegraph query "serializeProxyReference" --path D:\chatgpt2api
codegraph query "proxyReferenceLabel" --path D:\chatgpt2api
```

目的：

- 确认系统设置页面、代理页、图片管理页都通过 `api/settings.ts` 生成后端保存 payload。
- 确认账号页和账号列表不再自己拆 `direct`、`group:<id>`、`profile:<id>` 这类代理引用。

### 前端偏好存储

```powershell
codegraph query "preferenceKeys" --path D:\chatgpt2api
codegraph query "getNumberPreference" --path D:\chatgpt2api
codegraph query "getJsonPreference" --path D:\chatgpt2api
```

目的：

- 确认侧边栏折叠、账号分页、日志 limit、图片管理 page size、公开日志折叠、画图本地对话和本地 task id 等 UI 偏好都走 `web-vue/src/lib/preferences.ts`。
- 区分认证存储和 UI 偏好：`web-vue/src/api/client.ts` 的登录 token 仍直接使用 `localStorage`，不迁入偏好 adapter。

## 用法准则

- codegraph 适合定位和影响面分析，不替代读源码。
- 查到可疑符号后，还要打开对应文件确认具体条件和错误处理。
- 生成报告时，报告应由人根据 codegraph 结果和源码证据整理，不要把 query 输出当最终结论。
- 每次改完大结构后重新跑 `codegraph status`，确认索引最新。
