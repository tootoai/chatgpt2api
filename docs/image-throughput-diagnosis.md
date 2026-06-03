# 图片吞吐与排队诊断

这份文档用于回答一个具体问题：图片任务到底是卡在带宽、图生图上传、账号池，还是上游生成/轮询。

## 先给结论

排队可能和带宽有关，但不能直接判定为“带宽不够”。

当前代码里，即使前端或任务接口要求 `response_format: "url"`，后端仍然可能下载上游图片，再保存成本地 URL 返回。因此“返回 URL”只能说明前端少拿了 base64，不代表服务端完全不走图片流量。

证据：

- `services/image_task_service.py` 给任务 payload 写入 `response_format: "url"`。
- `services/image_task_service.py` 的恢复轮询仍调用 `backend.download_image_bytes(image_urls)`。
- `services/protocol/conversation.py` 在拿到 `image_urls` 后也调用 `backend.download_image_bytes(image_urls)`，再交给 `format_image_result()`。
- `api/image_inputs.py` 对图生图 `image_url` 会先下载远程图片，最大 50MB。
- `services/openai_backend_api.py` 的 `_upload_image()` 会执行 decode、inspect、register、blob_put、mark_uploaded。

所以图生图比文生图更可疑，因为它多了输入图片下载、读取、上传、注册 file id 这些阶段。大图、慢 URL、代理不稳、上游上传慢，都可能占住账号并发槽，造成后面任务排队。

## 排队不是一个点

图片任务至少分成这些阶段：

```mermaid
flowchart LR
  Submit["提交请求"] --> Queue["进入本地队列"]
  Queue --> Account["获取账号和并发槽"]
  Account --> Input["读取/下载参考图"]
  Input --> Upload["上传参考图到上游"]
  Upload --> SSE["提交上游会话/SSE"]
  SSE --> Poll["轮询图片结果"]
  Poll --> Download["下载结果图"]
  Download --> Store["保存/返回 URL"]
```

每一段慢，用户看起来都像“排队”。必须给每段打点，否则只能猜。

## 需要新增的诊断字段

任务级字段：

| 字段 | 含义 | 用途 |
| --- | --- | --- |
| `task_id` | 本地图片任务 ID | 前端、日志、运行时关联 |
| `client_task_id` | 前端幂等 ID | 防止重复提交 |
| `stage` | 当前阶段 | 判断卡在哪里 |
| `status` | queued/running/succeeded/failed/cancelled/expired | 统一状态 |
| `model` | 请求模型 | 按模型统计成功率 |
| `mode` | generate/edit | 区分文生图和图生图 |
| `size` | 图片尺寸 | 大尺寸失败率和耗时分析 |
| `n` | 图片数量 | 多图并发影响 |
| `account_email` | 实际使用账号 | 排查账号限流和异常 |
| `conversation_id` | 上游会话 ID | 恢复轮询和上游追踪 |
| `error_code` | 结构化错误码 | 前端分类展示 |
| `error_message` | 给用户看的错误 | 避免只显示原始 JSON |
| `raw_error` | 原始错误 | 管理员排查 |

耗时字段：

| 字段 | 含义 | 判断 |
| --- | --- | --- |
| `queued_wait_ms` | 从提交到开始运行 | 高说明 worker/账号/准入不足 |
| `account_acquire_ms` | 获取账号和槽位耗时 | 高说明号池或并发槽不足 |
| `input_fetch_ms` | 下载/读取参考图耗时 | 高说明图生图输入慢 |
| `input_bytes` | 参考图总字节数 | 大图导致上传慢的证据 |
| `upload_ms` | 上游图片上传耗时 | 高说明图生图上传或上游文件服务慢 |
| `upstream_sse_ms` | 上游会话首段响应耗时 | 高说明上游接单慢 |
| `poll_ms` | 轮询图片结果耗时 | 高说明上游生成慢或异步出图 |
| `result_download_ms` | 下载结果图耗时 | 高说明输出带宽/存储慢 |
| `store_ms` | 保存图片耗时 | 高说明本地磁盘/WebDAV/R2 慢 |
| `total_ms` | 总耗时 | 用于吞吐容量估算 |

事件字段：

| 事件 | 含义 |
| --- | --- |
| `image_task_queued` | 任务已入队 |
| `image_task_started` | worker 开始处理 |
| `image_account_acquired` | 已拿到账号槽位 |
| `image_input_fetch_start` | 开始读取/下载参考图 |
| `image_input_fetch_complete` | 参考图读取完成 |
| `image_upload_prepare` | 准备上传参考图 |
| `image_upload_registered` | 上游文件注册完成 |
| `image_upload_complete` | 上游文件上传完成 |
| `image_upstream_submitted` | 上游会话已提交 |
| `image_sse_complete` | SSE 初段完成 |
| `image_poll_start` | 开始轮询 |
| `image_poll_complete` | 轮询拿到图片 |
| `image_result_download_start` | 开始下载结果图 |
| `image_result_download_complete` | 结果图下载完成 |
| `image_task_succeeded` | 任务成功 |
| `image_task_failed` | 任务失败 |

现有 `image_upload_prepare`、`image_upload_registered`、`image_upload_complete`、`image_upload_failed` 已经是正确方向，但它们现在更像运行日志事件，新前端还没有完整展示。

## 错误分类

前端和日志都应该使用结构化错误码，不要只靠字符串。

| 错误码 | 解释 | 前端提示 |
| --- | --- | --- |
| `no_available_account` | 没有可用账号或并发槽 | 账号池繁忙或不可用 |
| `account_limited` | 账号被限流 | 换账号或等待额度恢复 |
| `input_fetch_failed` | 参考图 URL 下载失败 | 输入图片不可访问 |
| `input_too_large` | 参考图超过限制 | 压缩参考图 |
| `image_upload_failed` | 参考图上传到上游失败 | 图生图上传失败 |
| `invalid_referenced_image_id` | 模型/上游返回了无效图片引用 | 上游没有真正生成图片 |
| `upstream_text_reply` | 上游返回文本而不是图片资产 | 显示原始文本并允许继续轮询 |
| `poll_timeout` | 有会话但轮询超时 | 提供恢复轮询 |
| `result_download_failed` | 结果图下载失败 | 输出下载或存储失败 |
| `content_policy` | 内容策略拒绝 | 显示合规提示 |
| `network_timeout` | 网络超时 | 提示网络或代理问题 |
| `unknown` | 未分类 | 展示原始错误详情 |

## 怎么判断是不是带宽

带宽问题会有明确形态：

- `input_fetch_ms` 高，同时 `input_bytes` 大：参考图下载慢。
- `upload_ms` 高，同时 `input_bytes` 大：图生图上传慢。
- `result_download_ms` 高：结果图下载慢。
- 同一时间文生图也慢，但 `account_acquire_ms` 不高：可能是出口网络或上游响应慢。
- 大量任务都卡在 `poll_ms`：更像上游生成慢，不是带宽。
- 大量任务都卡在 `account_acquire_ms`：更像账号槽位不足，不是带宽。

所以要先看阶段耗时。没有这些字段时，不能把“排队”归因到带宽。

## 1000 图片任务/分钟下的带宽估算

如果每张结果图按 2MB 算：

```text
1000 images/min = 2000 MB/min = 33 MB/s = 约 266 Mbps
```

这只是结果图。图生图还要加参考图下载、参考图上传、重试、缩略图、日志和存储同步。

如果后端继续下载结果图并保存，本地服务建议至少按 500 Mbps 以上规划；如果图生图占比高，或者单图经常 5-10MB，需要继续上调。

## 推荐验证方法

第一步先做观测，不先改架构。

1. 给现有 Python 图片链路补阶段打点。
2. 对文生图、单参考图、三参考图分别跑压测。
3. 统计每个阶段 P50/P90/P99。
4. 把失败日志按 `error_code` 聚合。
5. 按 `account_email` 聚合失败率，区分账号问题和全局问题。
6. 按 `mode=generate/edit` 聚合耗时，确认图生图是否明显更慢。

最小压测分组：

| 分组 | 输入 | 目标 |
| --- | --- | --- |
| A | 文生图，无参考图 | 测上游生成和结果下载 |
| B | 图生图，1 张 1MB 参考图 | 测普通上传链路 |
| C | 图生图，3 张 5MB 参考图 | 测大输入压力 |
| D | 图生图，远程 image_url | 测输入 URL 下载 |
| E | 图生图，故意慢 URL | 验证 `input_fetch_ms` 是否能定位 |

## 新前端显示建议

图片任务详情页不要只显示成功/失败，至少显示：

- 当前阶段。
- 队列等待时间。
- 账号获取时间。
- 参考图大小。
- 上传耗时。
- 上游生成/轮询耗时。
- 结果下载耗时。
- 账号邮箱。
- conversation id。
- 原始上游文本回复。
- 是否可以恢复轮询。

这样用户看到失败时，能分辨：

- 是图片 URL 下载失败。
- 是上传失败。
- 是上游返回文本没有出图。
- 是轮询超时但可能还能恢复。
- 是账号池排队。

## 当前判断

基于当前代码，图生图失败和排队的优先排查顺序是：

1. 上游返回文本但没有图片资产。
2. 参考图上传阶段慢或失败。
3. 账号槽位被长任务占住。
4. poll 时间过长。
5. 结果图下载和本地存储慢。
6. 整体出口带宽不足。

带宽要规划足，但现在不能只盯带宽。真正要做的是把阶段耗时写进日志和任务详情。
