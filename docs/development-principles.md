# 开发准则

## 目标

这个项目的核心不是普通聊天 UI，而是一个 ChatGPT Web 上游代理和图片生成控制台。开发目标是：稳定、可诊断、可恢复、接口清晰。

## 总原则

1. 稳定优先
   - 现有后端已能跑，前端重写阶段不要顺手大拆后端。
   - 涉及图片链路、账号池、日志、限流、上传的改动必须小步提交，并配测试。

2. 接口先行
   - 前端改造先按 [api-contract.md](api-contract.md) 接口契约写。
   - 页面不能直接猜后端字段；所有字段都要在 API 类型或适配函数里明确。

3. 长任务必须任务化
   - 新前端图片生成优先走 `/api/image-tasks/generations` 和 `/api/image-tasks/edits`。
   - `/v1/images/*` 保留给 OpenAI 兼容客户端，不作为新控制台主交互。

4. 日志要服务排错
   - 图片失败日志必须尽量保留 `account_email`、`conversation_id`、`endpoint`、`request_text`、`error`。
   - 上游返回文本但没有图片时，错误不能只显示 400；要让用户看到“上游实际回复了什么”或至少看到可诊断摘要。

5. 前端只做一层 API 入口
   - 不允许页面里到处散落 `fetch`。
   - Vue 前端迁移时统一改 `src/api/*.ts` 和类型定义，页面只调用 API module。

6. 图表要有用途
   - 允许 ECharts，但只做运维图表。
   - 不做装饰型图表，不做影响加载速度的大动画。

7. 认证和密钥不要泄露
   - 账号 token、refresh token、cookie、OAuth callback、backup 密钥都不能完整显示在日志或页面里。
   - 导出功能必须明确用户操作，不自动下载敏感数据。
   - 管理员 key 才能进入完整控制台和调用文本、搜索、调试、PPT/PSD 等管理/调试能力；普通 user key 只作为画图入口使用，前端只显示画图页，后端也只保留图片相关能力。

8. 发布要可回滚
   - Docker 镜像仍由版本 tag 触发打包。
   - 发版前至少跑图片链路相关单测、API smoke、前端 build。

9. 区分现状和目标
   - 文档里必须写清楚某个字段是“当前已有”还是“建议新增”。
   - 前端不能依赖建议字段，除非对应后端代码已经实现并测试通过。

10. 历史代码不照抄
   - 当前 Next 前端和 gemini-web2api 前端都只能当参考。
   - 迁移时必须重新核对后端真实路由，尤其是 `/admin/*`、`/api/proxy`、登录状态这类接口。

## 后端改动准则

- 路由层只做认证、参数解析、日志包装和调用服务。
- 业务逻辑放在 `services/`。
- 图片链路的异常要带上上下文，不要只返回字符串。
- 新增聚合接口时优先读现有服务，不复制业务逻辑。
- 修改账号池并发、选号、限流时必须确认 `release_image_slot` 会被执行。

## 前端改动准则

- 以控制台为第一视角：概览、账号、任务、日志、画廊、设置。
- 每个页面必须有加载、空状态、错误状态。
- 图片任务页面必须支持刷新、轮询、失败恢复。
- 日志页面必须支持按 endpoint、status、account_email、conversation_id、时间筛选。
- 画廊页面必须支持图片预览、复制 URL、下载、删除、标签。
- API adapter 是前端重写的第一优先级；页面不能绕开 adapter 直接请求后端。
- 现有 `gemini-web2api` 页面里的 lane、fast/thinking/pro、cookie resolve、public display 先删除或隐藏。
- 新增图表必须能点击追到具体日志、账号或任务，否则先不做。

## 文档准则

每次开始一个较大阶段前，先补齐对应文档：

- 后端逻辑不清楚时，补 [backend-map.md](backend-map.md) 和 [image-pipeline.md](image-pipeline.md)。
- 前端不知道接什么时，补 [api-contract.md](api-contract.md) 和 [frontend-page-spec.md](frontend-page-spec.md)。
- 发现接口不匹配时，补 [backend-frontend-gap.md](backend-frontend-gap.md)。
- 要动后端结构时，补 [refactor-guide.md](refactor-guide.md) 或新增 ADR。

文档必须有证据来源：文件路径、接口路径、测试名或日志样例。不要只写感觉。

## 测试准则

后端至少保留这些验证：

- `python -m unittest discover -s test`
- `python -m compileall services api`
- 图片协议相关单测
- 账号池和日志上下文单测
- `/api/image-tasks/*` 基本流程测试
- 真实 localhost/上游 smoke 必须由 `CHATGPT2API_RUN_LIVE_HTTP_TESTS=1` 显式开启，不能混进默认单测
- 测试辅助模块统一放在 `test/helpers.py`，不要新增 `test/utils.py`，避免遮蔽项目自己的 `utils` 包

前端至少保留这些验证：

- `npm run build`
- 登录跳转 smoke
- 概览页图表非空 smoke
- 账号页列表、筛选、批量操作 smoke
- 日志详情打开 smoke
- 画廊图片预览 smoke

## 不做的事

- 不在前端阶段重写 `conversation.py`。
- 不把注册机直接塞进主控制台第一版。
- 不为了套 `gemini-web2api` 前端而把后端接口全部改成 `/admin/*`。
- 不让图片生成页面直接等待长请求到浏览器超时。
- 不把“上游返回文本但没出图”伪装成普通 400。
- 不把账号 token、refresh token、cookie、OAuth 回调完整展示在 UI 或日志里。
