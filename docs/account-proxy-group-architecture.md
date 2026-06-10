# 账号组与代理组架构方案

更新日期：2026-06-06

这份文档用于落地 `docs/control-panel-issue-audit.md` 里的 P1：账号组、真正代理组、账号组绑定代理组。目标不是马上重写全部调度，而是先把结构补出来，让前端和后端有清晰接口，后续再逐步把真实请求链路切到更完整的代理健康调度。

## 当前事实

- 账号已经存到 SQLite，但每个账号仍是一个 JSON blob。
- 账号里已有 `proxy` 字段，新控制台前台目标支持空值、`direct`、`group:<id>`、自定义代理 URL。
- 现有 `proxy_profiles` 属于后端历史兼容数据，不再作为新控制台的前台管理方案。
- 现有请求代理解析优先级是：显式入参代理 > 账号 proxy > 账号组默认代理组 > 全局 proxy > 直连。
- 后端主请求链路已逐步接入统一代理解析；注册机仍保留独立代理配置。

## 第一版目标

第一版先补真实结构和管理接口：

- 账号新增 `group_id` 字段。
- 配置新增 `account_groups`，用于保存账号组元信息。
- 配置新增 `proxy_groups`，每个代理组包含多个 `nodes`。
- 账号组可以绑定一个 `proxy_group_id`。
- 请求代理解析新增 `group:<id>` 引用。
- 账号没有单独 proxy 时，允许从账号组绑定的代理组选择节点。
- 新控制台前台不展示历史 profile 管理入口；账号编辑里的旧 `profile:<id>` 选择也已移除，只保留历史账号兼容解析。

## 暂缓内容

以下内容不在第一版强行完成：

- 不把所有外部请求失败自动写回代理节点健康状态。
- 不把 `proxy_profiles` 立即删除或迁移。
- 不接微软/webfree 注册机。
- 不做 Redis/跨容器代理租约。
- 不改图片核心请求链路的大结构。

原因：现有 Python 请求分支较多，直接把失败冷却插进所有 `curl_cffi` 请求风险偏高。第一版先把“可管理、可绑定、可测试”的结构补齐，再接统一代理 adapter。

## 数据模型

### account_groups

保存在 `config.json`：

```json
{
  "id": "microsoft",
  "name": "微软账号",
  "proxy_group_id": "hk-pool",
  "enabled": true,
  "notes": ""
}
```

字段含义：

- `id`：稳定标识，前端和账号字段引用。
- `name`：显示名。
- `proxy_group_id`：账号组默认使用的代理组，可为空。
- `enabled`：是否启用该组。
- `notes`：备注。

### account.group_id

保存在账号 JSON blob：

```json
{
  "access_token": "...",
  "source_type": "codex",
  "group_id": "microsoft"
}
```

规则：

- 空值表示未分组。
- 删除账号组不会删除账号，会把绑定账号的 `group_id` 清空为未分组。
- 后续可以按 `source_type` 自动推荐分组，但不在第一版强制改。

### proxy_groups

保存在 `config.json`：

```json
{
  "id": "hk-pool",
  "name": "香港代理池",
  "strategy": "round_robin",
  "enabled": true,
  "notes": "",
  "nodes": [
    {
      "id": "hk-1",
      "url": "http://user:pass@host:port",
      "enabled": true,
      "last_latency_ms": 0,
      "fail_count": 0,
      "last_error": "",
      "cooldown_until": ""
    }
  ]
}
```

字段含义：

- `strategy` 第一版只支持 `round_robin`。
- `nodes` 是真正代理节点列表。
- `cooldown_until` 是 ISO 字符串，选择节点时跳过仍在冷却的节点。
- 测试代理节点时可以写回延迟和错误状态。

## 代理优先级

最终优先级固定为：

1. 显式入参代理。
2. 账号单独 proxy。
3. 账号 proxy 为 `direct` 时强制直连，并停止继续查找。
4. 账号 proxy 为 `group:<id>` 时使用代理组节点。
5. 账号没有 proxy 时，读取 `account.group_id` 对应的账号组，再读取账号组绑定的 `proxy_group_id`。
6. 全局 proxy。
7. 直连。

补充规则：

- `group:<id>` 指向的代理组不存在、禁用或无可用节点时，会继续尝试账号组默认代理组，再尝试全局代理。
- 账号组不存在、禁用或未配置代理组时，会继续尝试全局代理。
- 代理组节点选择会跳过禁用节点、空 URL 节点和仍在 `cooldown_until` 之前的冷却节点。
- 旧 `profile:<id>` 仍可在后端解析，但只作为历史兼容，不作为新控制台的主路径。

## API 规划

账号组：

- `GET /api/account-groups`
- `POST /api/account-groups`
- `DELETE /api/account-groups/{group_id}`
- `POST /api/accounts/group` 批量绑定账号组

代理组：

- `GET /api/proxy/groups`
- `POST /api/proxy/groups`
- `DELETE /api/proxy/groups/{group_id}`
- `POST /api/proxy/groups/test` 测试代理组或节点

前台约定：

- 代理管理页只维护全局代理和代理组。
- 新代理组用 `group:<id>` 引用。
- 历史 profile 数据属于后端兼容，不在新控制台前台文档里作为使用方案展开。

## 后续增强

第二步再做：

- 所有请求通过统一代理 adapter 发起，失败时调用代理健康写回。
- 节点失败自动冷却，冷却后自动恢复候选。
- 同账号 stickiness，避免同一账号频繁换出口。
- 账号组按来源自动分组，例如 microsoft、domain-mail、codex、manual-token。
- 多容器部署时把账号/代理健康切到 PostgreSQL 或 Redis。

## 2026-06-06 代理链路复核

已统一到 `services.proxy_service.proxy_settings.build_session_kwargs(...)` 或同等解析规则的链路：

- ChatGPT 主后端 session：`OpenAIBackendAPI.__init__` 会按账号、账号组和全局代理创建 `curl_cffi` session。
- Codex 图片 responses：`/backend-api/codex/responses` 已从 `urllib.request` 切回 `OpenAIBackendAPI.session.post(...)`，不再绕过账号代理、账号组代理或全局代理。
- 账号 token 刷新：refresh-token keepalive 使用当前账号对象解析代理。
- 密码重登：邮箱密码 OAuth 登录使用统一代理 session；没有具体账号对象时按全局代理回退。
- URL 图片输入下载、内容过滤、OAuth callback 登录、CPA 远程导入、Sub2API 远程读取都使用统一代理 session。

仍然独立的链路：

- `services/register/*` 的微软/webfree 注册机代理属于注册流程自己的代理 lane，由注册机配置注入，不跟账号请求代理组混用。
- `services.backup_service` 和 `services.image_storage_service` 面向备份/存储目标，不默认套 ChatGPT 上游代理；后续如果要给 WebDAV/R2 单独代理，应单独建存储代理配置。

## 回归测试

已覆盖的代码级契约：

- `test/test_proxy_service.py`：代理解析优先级、`direct` 强制直连、账号/账号组/全局代理回退、代理组 round-robin 跳过禁用和冷却节点、旧 `profile:<id>` 兼容。
- `test/test_accounts_api.py`：账号组列表后端计数、缺失代理组保存失败、同名账号组保存失败、删除账号组清空绑定账号。
