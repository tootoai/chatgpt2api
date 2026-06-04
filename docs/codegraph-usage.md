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
Files: 200
Nodes: 3,896
Edges: 8,118
Routes: 81
Backend: node:sqlite
```

2026-06-04 已执行 `codegraph sync D:\chatgpt2api`，同步提示：`Synced 147 changed files`，新增 142 个文件变更记录、修改 5 个文件变更记录、新增 2,686 个节点。

## 常用命令

```powershell
codegraph status D:\chatgpt2api
codegraph query "ImageTask" --path D:\chatgpt2api
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

2026-06-04 结论：

- `exportAccounts` 有两层：页面逻辑函数 `web-vue/src/views/accounts/useAccountsPage.ts` 和 API adapter 函数 `web-vue/src/api/reverseAccounts.ts`。
- 页面层调用者是 `handleExportSelected` 和 `handleExportAll`。
- 后端出口是 `api/accounts.py` 的 `POST /api/accounts/export`。
- `loadCPAFiles`、`loadSub2APIAccounts` 影响范围集中在 `useAccountsPage.ts`。
- CodeGraph 没有完整识别 Vue template 里的 `@click="loadCPAFiles"`、`@click="loadSub2APIAccounts"` 调用，Vue 模板入口必须继续配合 `rg` 检查。

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

### 前端接口

```powershell
codegraph query "fetchImageTasks" --path D:\chatgpt2api
codegraph query "fetchSystemLogs" --path D:\chatgpt2api
codegraph query "fetchProxy" --path D:\chatgpt2api
```

目的：

- 查当前前端有没有调用后端不存在的接口。
- 查新 Vue 前端迁移时哪些函数可以复用，哪些必须重写。

## 用法准则

- codegraph 适合定位和影响面分析，不替代读源码。
- 查到可疑符号后，还要打开对应文件确认具体条件和错误处理。
- 生成报告时，报告应由人根据 codegraph 结果和源码证据整理，不要把 query 输出当最终结论。
- 每次改完大结构后重新跑 `codegraph status`，确认索引最新。
