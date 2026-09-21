# 系统架构 v1.0

## 组件

- Web：React SPA，Nginx 托管，REST + SSE。
- API：FastAPI，无状态服务。
- PostgreSQL：`app` 平台数据、`mart` 经营数据。
- LLM Adapter：OpenAI-compatible，服务端持有密钥；真实 Agent 编排负责 SQL 生成、一次受控纠错和结果总结。
- Agent Runtime：LangGraph `StateGraph`，确定性节点与模型节点显式分离。
- Vector RAG：PostgreSQL `pgvector` + 本地中文 Embedding，保存 Schema、指标、Join 和 Few-shot 向量。
- 可选 Redis：MVP 不依赖；扩展时用于取消信号和限流。

## 请求链路

1. 前端创建问题，API 保存用户消息和 queued 执行。
2. 前端订阅执行 SSE。
3. LangGraph 装载会话上下文和结构化工作记忆。
4. Hybrid Retriever 组合 pgvector 语义召回和关键词召回，得到 Schema、指标、Join 和 Few-shot。
5. SQL Agent 节点调用真实模型生成结构化候选 SQL。
6. Validator 节点执行 AST 安全校验；通过后由只读连接在超时/行数限制下执行。
7. 可恢复数据库错误最多进入一次纠错分支，纠错 SQL 必须重新完整校验。
8. Summary Agent 使用受限结果 JSON 生成答案、图表建议和追问；Verifier 核验关键数字和图表字段。
9. LangGraph 保存 checkpoint，业务服务保存执行、消息和回答版本。
10. SSE 发节点进度和完成事件；执行详情 API 是最终事实来源。

## 模块边界

```text
api -> services -> repositories
               -> text2sql/{schema,llm,validator,executor,answer}
```

API 层不写 SQL；LLM 适配器不访问数据库；执行器不能绕过 Validator；问数连接不能访问 `app` Schema。

Fake Adapter 不是演示或生产降级方案。它只允许在 `test`、CI 或显式 `local` 离线模式使用；`demo`、`prod` 未配置真实模型时必须失败关闭。

## Agent State

状态至少包含：`executionId`、`sessionId`、规范化问题、最近消息、结构化记忆、检索文档、允许对象、模型输出、SQL 校验状态、纠错次数、查询结果、回答包、错误和取消标志。节点只读写声明字段，不通过全局变量传递业务状态。

## 向量数据边界

- `app.rag_documents` 保存知识文档元数据、内容哈希、Embedding 模型版本和向量；不保存 API Key、数据库连接串或完整业务事实行。
- 知识类型仅包括 Schema、字段、指标、Join、口径说明和审核后的 Few-shot。
- RAG Repository 使用平台账号访问 `app`；`text2sql_ro` 仍只能查询 `mart` 白名单视图。
- 默认使用 512 维中文向量和 cosine distance；小规模知识库先精确检索，数据量增长后再启用 HNSW。

## 一致性

- 创建消息与执行记录同一事务。
- 外部模型和查询不持有平台数据库长事务。
- 完成时以短事务写答案版本和最终状态。
- SSE 是状态通知，执行详情 API 是最终事实来源。
