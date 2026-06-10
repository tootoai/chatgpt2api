# 测试治理

更新时间：2026-06-10

这份文档用于区分默认可跑的本地回归、只读 smoke、真实上游/localhost smoke，以及带副作用的手动验收。目标是让 `python -m unittest discover -s test` 成为稳定的默认反馈环，而不是被真实服务、上游网络或本地污染数据拖挂。

## 默认本地回归

默认回归不依赖正在运行的 `127.0.0.1:8000`，也不访问 ChatGPT 上游。

```powershell
python -m unittest discover -s test
```

2026-06-10 当前结果：

```text
Ran 154 tests in 3.950s
OK (skipped=17)
```

前端构建回归：

```powershell
cd web-vue
npm run build
```

2026-06-10 当前结果：通过。

## Live HTTP smoke

直接调用本地服务或上游的测试默认跳过，只有明确要做真实 smoke 时才打开：

```powershell
$env:CHATGPT2API_RUN_LIVE_HTTP_TESTS="1"
python -m unittest test.test_v1_chat_completions test.test_v1_images_generations test.test_v1_images_edits test.test_v1_messages test.test_v1_models test.test_v1_responses
```

默认跳过的原因：

- 这些测试会请求 `http://127.0.0.1:8000` 或真实上游。
- 图片链路可能等待很久，容易把普通单测变成网络稳定性测试。
- 真实生图、编辑图、模型列表等 smoke 需要测试账号、代理组、图片输入和风险确认。

开关和装饰器放在：

```text
test/helpers.py
```

不要再新增 `test/utils.py`。`unittest discover -s test` 会把它作为顶层 `utils` 模块导入，从而遮蔽项目自己的 `utils` 包，导致 `utils.helper`、`utils.log` 等导入失败。

## 存储层契约

账号池默认已经切到 SQLite，本地数据库路径由配置决定，常见为：

```text
data/accounts.db
```

当前存储层必须覆盖这些契约：

- `count_accounts()`
- `upsert_accounts(...)`
- `delete_accounts(...)`
- `delete_accounts_by_status(...)`
- `replace_account(...)`
- `list_accounts_page(...)`

相关回归：

```powershell
python -m unittest test.test_database_storage test.test_storage_backend test.test_account_invalid_removal
```

`DatabaseStorageBackend.list_accounts_page(...)` 目前仍基于 `accounts.data` JSON 读出后做过滤、统计和分页。它是现有 SQLite 结构下的保守实现，不代表已经把账号字段完全列式化；如果后续 1w 账号场景出现真实性能瓶颈，再单独做索引列迁移。

## 测试数据边界

协议层测试不能把假的图片 bytes 写入真实图库。需要图片 fixture 时使用有效 tiny PNG，或者 mock `image_storage_service.save()`。

已经出现过的问题：测试曾把 `b"generated image"` 写成 `.png`，污染了 `data/images` 和 `data/image_index.json`，前端就会出现“无法预览”的假图。

图片存储相关规则见：

```text
docs/control-panel-code-map.md
docs/frontend-rewrite-status.md
```

## 发布前建议顺序

```powershell
python -m unittest discover -s test
cd web-vue
npm run build
codegraph sync D:\chatgpt2api
codegraph status D:\chatgpt2api
```

只有在指定测试账号、测试代理组和测试图片后，再执行 live HTTP smoke 或 R2-R4 手动动作。
