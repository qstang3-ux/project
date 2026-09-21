# 接口契约变更记录

## 2026-09-18

- `ExecutionDetail` 新增必填 `tokenUsage`，回答卡可直接展示本次执行的输入、输出和总 Token。
- `ExecutionStep.durationMs` 改为真实节点墙钟耗时；历史零耗时的模型步骤从脱敏模型审计记录回填，其余无可靠数据时返回 `null`，不再伪造 `0ms`。

## 2026-09-16

- Prompt Injection 四通道隔离、RAG/查询结果数据面标记及 execution `context_provenance` 均属于后端
  内部安全实现，不改变现有 REST/SSE 成功响应字段，前端无需因这些内部字段重新生成类型。
- 显式 `contextMessageIds` 现在严格要求消息属于当前 session，且其 execution 已完成并为
  `data_query`；不满足时返回既有统一错误结构中的 HTTP 422 / `CONTEXT_NOT_ALLOWED`。请求体 Schema
  与成功响应字段不变。
- resubmit 不再自动继承 `sourceMessageId` 正文；regenerate 使用原 execution 的上下文快照；
  clarification 只合并同 execution 的补充内容。以上均为上下文解析语义收紧，不新增外部字段。

- SSE 改为读取持久化 append-only execution event，不再在每个连接中根据 execution/step 临时拼接历史。
- SSE event ID 固定为 `<execution UUID>:<sequence>`；`Last-Event-ID` Header 优先，新增
  `lastEventId` query fallback。重连只返回游标之后的事件。
- 新增 `execution.completed` 终态事件；started 与终态事件在单个 execution 内均只出现一次。
- 非法、跨 execution 和已过保留期游标分别返回 `SSE_EVENT_ID_INVALID`、
  `SSE_EVENT_EXECUTION_MISMATCH` 和 `SSE_EVENT_EXPIRED`。本次契约会影响生成的 SSE 类型，
  前端后续需要基于最新 OpenAPI 重新生成类型，但本批次不修改前端实现。

- 新增的 execution effect 账本、worker 租约、心跳和有界恢复属于后端内部机制；
  本批次不改变 REST/SSE 的对外成功响应字段，前端无需重新生成类型。
- 新增稳定内部错误码 `EXECUTION_LEASE_LOST`，只在 worker 已失去该 execution 租约时阻止旧实例提交；
  正常客户端提交与查询契约不变。

- 创建查询、提交澄清、编辑重发和重新生成的 `Idempotency-Key` 现在全局绑定
  operation、目标 session/message/execution 和规范化请求体指纹。完全相同的重试仍返回
  原 `QueryAccepted`；任一绑定不同时返回 HTTP 409 / `IDEMPOTENCY_KEY_CONFLICT`。
- 上述四个接口的 OpenAPI 显式声明 409 错误响应；成功响应字段不变。
- 执行取消和后台完成/失败/拒绝采用条件终态更新，已取消的执行不会被后台线程覆盖。

- `ExecutionStatus` 新增 `awaiting_input`。该状态是正常可交互等待态，不应渲染为 SQL 失败。
- 新增 `POST /qa/executions/{executionId}/clarifications`：必须携带 `Idempotency-Key`，请求体为
  `content`；成功后继续原 execution、原 graph thread 和 checkpoint，并返回 `QueryAccepted`。
- `ExecutionDetail` 与 `QaLogDetail` 新增 `intent`、`normalizedQuestion`、`missingSlots`、
  `clarificationRound`；`ExecutionDetail` 另新增可空 `clarification` 结构，包含提示、缺失槽位和轮次上限。
- SSE 新增 `clarification.required` 事件。前端收到后应停止等待 SQL 步骤，展示 clarification.prompt，
  并通过新增澄清接口提交用户补充；`awaiting_input` 不会被服务启动恢复扫描自动推进。
- `ModelCallAudit.purpose` 新增 `intent_classification`，便于区分分类、SQL、纠错和总结调用。
- 意图枚举为 `data_query`、`clarification`、`business_definition`、`product_help`、`chat`、
  `out_of_scope`、`unsafe`。只有 `data_query` 会产生 RAG/SQL 审计步骤。
- 图结构版本默认升级为 `langgraph-v2`；已有部署如在环境变量固定旧版本名，应同步调整以避免
  新旧节点轨迹混用。

- 第一阶段实现曾保持 `openapi.yaml` 的既有请求和响应字段不变。
- FastAPI 内部路径参数使用 Python 名称 `session_id`/`execution_id`，对外 URL 语义与契约中的 `sessionId`/`executionId` 相同；后续契约一致性测试按规范化路径比较。
- 契约审查后为 `ExecutionDetail` 增加必返的 `sqlValidationStatus`，取值为
  `not_started`、`passed` 或 `rejected`。
- `ExecutionDetail.result`、`chart`、`error` 改为必返但可空字段，并补充各状态下的存在条件。
- SSE `ExecutionEvent.data` 改为使用 `kind` 判别的结构化联合类型；服务端同步发送对应负载。
- 反馈和问答日志摘要增加 `userId`，列表接口增加 `userId` 筛选参数。MVP 值来自后端配置的
  固定系统用户，不接受客户端伪造。
- `FeedbackCreate.description` 上限收紧为 500 字符；推荐问题单条上限收紧为 100 字符；
  模型配置名称和模型名称上限分别收紧为 50 和 100 字符。
- 图表字段判别联合暂缓，前端继续以 `ResultSet.columns` 校验字段并在异常时降级为表格。
- 上述变更会影响生成类型，前端需要基于本版本 `openapi.yaml` 重新生成 API 类型。
- 模型配置新增必填 `protocol`，取值为 `responses` 或 `chat_completions`；
  `gpt-5.6-sol` 固定归一为 `responses`。
- 模型连接测试状态新增 `invalid_response`，HTTP 200 但 Content-Type、JSON 或响应结构无效时返回该状态。
- 问答日志详情新增 `modelCalls`，分别审计 SQL 生成、纠错和答案总结的模型、用途、耗时、Token、
  重试次数、状态和脱敏错误码。前端需再次基于最新 OpenAPI 生成类型。
- 问答日志详情新增 `graphVersion`、`graphNodeTrace`、`checkpointStatus`、`ragDocumentIds` 和
  `ragDegraded`，用于审计 LangGraph 图版本、节点轨迹、PostgreSQL checkpoint 和混合 RAG 状态。
  前端需基于本次契约再次生成类型。
# 2026-09-18：移除默认分析年份

- `ApplicationConfig` 与 `ApplicationConfigUpdate` 移除 `defaultAnalysisYear`。
- 用户未提供年份且上下文无法唯一确定时，进入澄清流程，不再由应用配置静默补充年份。
