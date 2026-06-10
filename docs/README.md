# chatgpt2api 架构与前端重写文档索引

这组文档用于在不破坏现有稳定后端的前提下，摸清后端逻辑、固定前端接口契约，并以本地 `D:\gemini2api\frontend` 的 Vue 控制台为交互参考，迁移成新的 chatgpt2api 控制台。

## 阅读顺序

1. [development-principles.md](development-principles.md)
   - 开发准则。先读这个，避免前端重写和后端适配变成随手改。
2. [test-governance.md](test-governance.md)
   - 测试分层和默认回归规则。说明哪些测试默认可跑、哪些 live HTTP smoke 需要 `CHATGPT2API_RUN_LIVE_HTTP_TESTS=1`，以及为什么不能再新增 `test/utils.py`。
2. [backend-map.md](backend-map.md)
   - 后端模块地图。说明路由层、服务层、账号池、日志、存储之间的关系。
3. [data-storage-map.md](data-storage-map.md)
   - 数据存储地图。说明概览、账号、系统设置、代理、日志、图片、账号组等分别保存在 SQLite、config.json、JSONL、文件目录还是浏览器 localStorage。
4. [image-pipeline.md](image-pipeline.md)
   - 图片链路专文。文生图、图生图、上传、轮询、失败重试都在这里。
5. [image-throughput-diagnosis.md](image-throughput-diagnosis.md)
   - 图片吞吐和排队诊断。用于判断卡在账号、图生图上传、上游轮询、结果下载还是带宽。
6. [api-contract.md](api-contract.md)
   - 给新前端使用的接口契约。以后 Vue 前端主要按这份接后端。
7. [frontend-adapter-map.md](frontend-adapter-map.md)
   - 本地 `gemini-web2api` 前端和 chatgpt2api 后端之间的页面、接口、字段适配表。
8. [frontend-interface-action-map.md](frontend-interface-action-map.md)
   - 新 Vue 控制台每个页面用哪些接口、按钮风险等级、哪些 smoke 可以直接做、哪些必须确认。
9. [frontend-rewrite-plan.md](frontend-rewrite-plan.md)
   - 新前端落地计划和页面开发顺序。
10. [frontend-page-spec.md](frontend-page-spec.md)
   - 新 Vue 控制台页面规格。每个页面该接什么接口、展示什么字段、注意什么风险。
11. [backend-frontend-gap.md](backend-frontend-gap.md)
   - 前后端缺口清单。区分已有接口、建议新增接口、不能照抄的旧接口。
12. [control-panel-issue-audit.md](control-panel-issue-audit.md)
   - 当前控制台问题审计和下一步决策。把用户反馈逐条拆成已做、半做、未做和后续顺序。
13. [refactor-guide.md](refactor-guide.md)
   - 后端重构候选项。最后读；当前阶段先不要大拆稳定逻辑。
14. [codegraph-usage.md](codegraph-usage.md)
   - codegraph 的项目内使用方法。它用于结构查询和影响面分析，不是自动报告生成器。
15. [1000-tpm-architecture-plan.md](1000-tpm-architecture-plan.md)
   - 面向 1000 图片任务/分钟的架构方案。比较纯 Python、Python+Go、全 Go，并给出推荐路线。
16. [go-image-runtime-contract.md](go-image-runtime-contract.md)
   - Python 控制面与 Go 图片数据面的内部契约草案。定义任务、事件、租约、错误和存储交接。

## 当前结论

- 后端先稳定保留，先补文档和接口聚合，不做大范围重构。
- 新前端建议以 `D:\gemini2api\frontend` 为交互参考，当前落点是 `web-vue/`。
- 新前端优先使用 `/api/image-tasks/*` 做图片任务，不直接把长时间图片请求绑在页面等待上。
- Dashboard 图表按原版模型维度保留：模型请求分布、调用趋势、成功率趋势、平均响应时间、模型调用占比、模型使用排行。
- 注册机暂时不进入主前端；后续作为独立任务模块接入。
- 当前 `web/src/lib/api.ts` 有少量历史残留接口，新 Vue 前端不要直接照抄，按缺口清单重写 API adapter。
- codegraph 已完成索引，可以辅助查图片链路、账号池和日志影响面，但报告需要结合源码整理。
- 1000 TPM 不建议直接全量 Go 重写；优先做 Python 控制面 + Go 图片数据面的混合架构。
- 返回 URL 不代表服务端零流量；当前链路仍可能下载结果图并保存成本地 URL。
- 图生图排队优先按阶段诊断：参考图下载/上传、账号槽位、上游轮询、结果下载，而不是先归因为带宽。
- 当前控制台不是最终完成态；账号组、多节点代理组、微软/webfree 注册机、支持模型最终口径、后端批量任务取消仍未完成，继续改代码前先看 `control-panel-issue-audit.md`。
