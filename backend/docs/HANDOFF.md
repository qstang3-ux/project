# 后端开发交接说明

## 目标

使用 FastAPI + SQLAlchemy + Alembic + PostgreSQL 实现真实可查询、可审计且安全的经营数据问数后端。

## 核心交付

- FastAPI 基础、统一错误和健康检查。
- `mart` 与 `app` 双 Schema。
- 固定 Seed 和语义视图。
- 数据源、会话、消息、问数执行 API。
- Fake Model Adapter 和 OpenAI-compatible Adapter；Fake 仅用于测试/CI/显式本地离线开发。
- LangGraph Typed StateGraph、PostgreSQL checkpoint 和 pgvector 混合 RAG。
- 独立意图分类、槽位检查、结构化澄清等待与同 execution/checkpoint 恢复。
- SQL AST 校验、白名单、LIMIT、超时和只读执行。
- 回答摘要和结构化图表建议。
- 模型配置、应用配置、反馈和校对 API。
- 8 条核心评测问题与 5 条危险请求测试。
- Docker 可运行，OpenAPI 与实现一致。

## 核心调用链

```text
API
→ QA Service
→ Text2SQL Orchestrator
→ Schema Retriever
→ Model Adapter
→ SQL Validator
→ Read-only Query Executor
→ Answer/Chart Builder
→ Execution Log
```

任何 Adapter 生成的 SQL 都必须走相同 Validator 和 Executor，Fake Adapter 也不例外。

## 数据归属

- `backend/data/schema.sql` 是设计参考，实际实现使用 SQLAlchemy 与 Alembic。
- `backend/docs/data/` 是业务口径和字段事实来源。
- 金额使用 Decimal/numeric 元，UI 自行换算万元。
- Seed 固定种子 `20260915`，数据截止日 `2026-05-31`。
- Text2SQL 账号只能访问 `mart` 白名单视图。

## API 所有权

- `backend/docs/api/openapi.yaml` 是唯一契约。
- 实现接口前补齐该资源的请求和响应 Schema。
- 契约变化必须同时通知前端，不允许只改实现。
- 错误统一包含 code、message、requestId 和脱敏 details。

## 核心评测问题

优先保证：目标 Top 5、北京月度收入趋势、低于 70% 完成率、产品线占比、行业排名、收入同比、高风险项目、应收 Top 10。

## 安全红线

- 不执行未通过 AST 校验的 SQL。
- 不允许 `app`、系统 Schema、DDL/DML、多语句和危险函数。
- 模型密钥不进入响应或日志。
- 数据库完整错误不返回前端。
- 不按问题写死业务答案；Fake Adapter 只能提供候选 SQL。
- SQL 安全拒绝不可通过模型纠错绕过。

## 推荐实现顺序

1. 项目骨架、配置、数据库和健康检查。
2. 模型、迁移、Seed、语义视图和断言。
3. 会话、消息和数据源 API。
4. Fake Adapter、Validator 和 Executor。
5. 问数 Orchestrator 和执行记录。
6. LangGraph 真实模型 Agent：向量 RAG、SQL 生成、一次受控纠错、结果总结、图表和追问；完成 checkpoint 和真实供应商冒烟。
7. 配置、反馈和日志。
8. 安全测试、评测、Docker 和清洁启动。

## 完成门禁

```text
ruff check .
ruff format --check .
mypy app
pytest
alembic upgrade head
```

最终报告必须列出迁移、Seed、接口、评测、安全用例、Docker 验证和已知问题的实际结果。

受控运行环境未配置真实模型时必须失败关闭，不得静默回退 Fake，也不得用 Fake 的评测结果声称真实 Agent 已通过。

## 当前运行状态（2026-09-18）

- `DEFAULT_MODEL_CONFIG=real`，当前启用配置为 DeepSeek `deepseek-flash`，使用 `https://api.deepseek.com/chat/completions`。
- API Key 已由配置 API 加密写入数据库，未写入 `.env`、仓库、前端或普通日志；接口只返回密钥是否存在和掩码。
- 连接测试成功；真实问题“查询2026年各经营单元商业目标完成率，按完成率升序”已走完整 LangGraph/RAG/Text2SQL 链路并完成，返回 21 行。
- DeepSeek 首次答案曾自行换算单位并生成派生阈值，被既有数字校验正确拒绝；当前通过零温度和严格复述规则解决，没有放宽安全校验。
- 已使用启用中的加密模型配置完成真实套件：8/8 条核心问数通过、5/5 条危险请求安全拒绝。脱敏报告为 `backend/.runtime/real-model-smoke-20260918-final.json`。
- 数据库保留一个完成态验收会话；真实模型冒烟产生的临时会话已清理。

## 执行恢复运维

- API 启动时最多扫描 `EXECUTION_RECOVERY_BATCH_SIZE` 条可恢复执行，不循环扫描。
- 手工恢复使用 `python -m app.recovery --limit 20`；`--limit` 必须为 1～100。
- 命令只领取 queued 或租约过期的 running，活动租约、`awaiting_input`、cancelled 和终态保持不变。
- 多实例通过 `EXECUTION_WORKER_ID`、`EXECUTION_LEASE_SECONDS` 和
  `EXECUTION_HEARTBEAT_SECONDS` 配置 owner 及续租；未指定 worker ID 时由进程生成唯一值。

## SSE 事件运维

- execution event 是 append-only 持久记录；SSE 连接只读取记录，不根据 execution 当前快照生成伪历史。
- `Last-Event-ID` 格式为 `<execution UUID>:<sequence>`；Header 优先于 `lastEventId` query fallback。
- poll、keepalive 和单批上限分别由 `EXECUTION_EVENT_POLL_INTERVAL_SECONDS`、
  `EXECUTION_EVENT_HEARTBEAT_SECONDS`、`EXECUTION_EVENT_BATCH_SIZE` 控制。
- 本地环境不启用定时清理。手工清理命令为
  `python -m app.event_retention --days 7 --limit 100`，只删除过期终态 execution 的事件；上线后可由
  外部调度器周期执行同一命令。

## Prompt 与上下文安全

- 模型请求使用可信 system 控制面和不可信 user 数据面。当前问题、历史、RAG、候选 SQL、固定错误
  类别和查询结果都位于带 channel/source/trust/provenance 的 `untrustedData` 中。
- Text2SQL 历史只允许同 session、已完成且 intent 为 `data_query` 的消息；execution 固化消息 ID 快照。
  普通会话历史单独装载，仅供意图分类和非 SQL 回答，并记录 `sqlEligible=false`，不得进入 SQL/RAG。
  resubmit 的来源消息仅记录 provenance，regenerate 复用原 Text2SQL 快照，空快照也不会吸入后来消息。
- RAG 文本不进入可信对象定义，也不能扩展 allowlist。SQL 纠错只接收固定可恢复错误类别，不接收
  PostgreSQL 原始异常文本；纠错结果仍重新执行完整 AST 校验。
- 迁移 `20260916_0012_context_provenance.py` 新增 `app.qa_executions.context_provenance`。
- 离线安全评测命令为
  `python scripts/evaluate_prompt_security.py --output .runtime/prompt-injection-report.json`，不调用付费模型。

## 回答分支与版本（2026-09-17）

- `POST /qa/messages/{messageId}/resubmit` 保留原消息和执行，创建独立会话分支。
- `POST /qa/messages/{messageId}/regenerate` 创建新的完整 Agent execution，并通过 `regenerated_from_execution_id` 记录父执行。
- `GET /qa/messages/{messageId}/versions` 会先回溯根执行，再聚合该会话内全部再生成后代；从原回答或任一后代回答查询均返回同一版本链，仅包含已有回答的完成态执行，最新版本标记为当前。
- `GET /qa/executions/{executionId}/export` 返回带 UTF-8 BOM 的 CSV，前端直接使用响应文件名下载。
- 本次新增回答版本单元测试；后端 Ruff、格式、MyPy 和默认测试集全部通过。PostgreSQL 集成用例已增加两端消息查询同一版本链的断言，需在显式注入 `TEST_APP_DATABASE_URL`、`TEST_QUERY_DATABASE_URL` 且使用 Fake 模型配置的隔离测试环境运行。

## 执行 Token 与步骤耗时（2026-09-18）

- `ExecutionDetail` 现按 OpenAPI 必须返回 `tokenUsage`，字段为 `promptTokens`、`completionTokens`、`totalTokens`；值来自执行记录中持久化的模型调用统计。
- LangGraph 节点进入时记录墙钟时间，步骤完成时计算真实毫秒耗时，不再统一写入 `0`。
- 历史执行中模型步骤若没有节点墙钟耗时，会使用对应模型调用审计耗时恢复；没有可靠来源的步骤返回 `null`，避免制造虚假精度。
- 问答执行详情和问答日志详情共用同一耗时计算器，保证两个页面口径一致。
