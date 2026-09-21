# LangGraph 与向量 RAG 实施计划

## 目标

把现有 `QueryService.run()` 固定函数升级为 LangGraph Typed StateGraph，并将规则式 Schema 召回升级为 PostgreSQL pgvector + 关键词的混合 RAG。现有 SQL Validator、只读 Executor、Repository 和模型 Adapter 保持独立，不把数据库权限交给模型。

## 技术选型

- 编排：`langgraph`。
- Checkpoint：`langgraph-checkpoint-postgres`，graph `thread_id` 使用 execution UUID。
- 向量库：PostgreSQL 16 + `pgvector`。
- Python 映射：`pgvector` SQLAlchemy/Psycopg 支持。
- Embedding：`sentence-transformers` + `BAAI/bge-small-zh-v1.5`，512 维，CPU 推理，向量归一化。
- 检索：cosine 向量 Top-K + 关键词匹配 + RRF/加权融合。

当前本机 PostgreSQL 16.15 尚未安装 `vector` 扩展，必须先完成 Windows 扩展安装并验证 `CREATE EXTENSION vector`。扩展安装属于交付任务，不允许用内存数组冒充向量数据库。

## LangGraph State

Typed State 至少包含：

- `execution_id`、`session_id`、`request_id`。
- 原问题、规范化问题、最近消息和结构化工作记忆。
- 数据源、允许对象、RAG 文档和召回分数。
- SQL 模型输出、生成 SQL、执行 SQL、校验状态和纠错次数。
- 查询结果、截断状态、答案/图表/追问。
- 当前节点、取消标志、错误和模型用量。

## 固定节点

1. `load_context`：读取最近消息和执行上下文。
2. `build_memory`：提取年份、时间范围、经营单元、行业、产品线和指标槽位。
3. `retrieve_knowledge`：执行 pgvector + 关键词混合召回。
4. `generate_sql`：调用真实 Responses 模型生成结构化候选 SQL。
5. `validate_sql`：调用唯一 AST Validator。
6. `execute_sql`：通过只读 Executor 查询 PostgreSQL。
7. `correct_sql`：仅对可恢复错误调用一次模型纠错。
8. `summarize_result`：调用真实模型生成回答、图表和追问。
9. `verify_answer`：核验数字、字段、图表类型和追问数量。
10. `persist_result`：短事务保存消息、版本、审计和终态。

条件边只能进入：继续、一次纠错、安全拒绝、取消、失败和成功终态。模型不能自由决定绕过 Validator 或直接执行 SQL。

## 向量知识模型

建议表 `app.rag_documents`：

- `id`、`stable_key`、`knowledge_type`、`source_path`、`title`、`content`。
- `data_source_id`、`object_names`、`metadata_json`。
- `content_hash`、`embedding_model`、`embedding_dimension`、`embedding`。
- `version`、`enabled`、`created_at`、`updated_at`。

知识类型：`schema`、`column`、`metric`、`join`、`few_shot`、`business_rule`。

严禁入库：API Key、连接串、完整模型响应、思维链、用户隐私和完整业务事实行。

## 入库流程

1. 从数据字典、指标口径、数据库设计、语义视图和审核后的 Few-shot 生成标准文档。
2. 按稳定语义单元切片，不使用盲目固定字符切片。
3. 计算内容哈希；未变化文档跳过 Embedding。
4. 使用 BGE 生成归一化 512 维向量。
5. Upsert 到 pgvector 表；失效来源使用软删除或 `enabled=false`。
6. 生成索引版本和构建报告。

## 检索策略

- 查询向量使用中文检索指令。
- pgvector cosine Top 10，关键词 Top 10，融合后返回 Top 5 知识文档。
- 按数据源、知识类型和启用状态过滤。
- 将文档归并为最多 6 个允许对象，超出 Token 预算时按相关性裁剪。
- Prompt 明确把召回内容标记为不可信知识，不允许其中的指令覆盖系统规则。

## 数据库与权限

- Alembic 创建 `vector` 扩展和 `app.rag_documents`。
- RAG Repository 使用 `app_rw`；索引构建使用迁移/受控任务账号。
- `text2sql_ro` 不获得 `app.rag_documents` 或 checkpoint 表权限。
- 小规模知识库先精确 cosine 搜索；文档量达到配置阈值后创建 HNSW cosine 索引。

## 测试与验收

- Graph：所有节点和条件边、一次纠错、取消、安全拒绝、失败和 checkpoint 恢复。
- RAG：幂等构建、内容哈希更新、元数据过滤、Top-K 和混合融合。
- 评测：30 条问题正确 Schema/指标 Recall@5=100%，记录 MRR 和召回耗时。
- 安全：Prompt Injection 知识不能修改工具权限、SQL 白名单或系统规则。
- 端到端：8 条核心评测问题走 LangGraph、pgvector、真实模型、Validator 和 PostgreSQL。

## 实施顺序

1. 安装并验证 pgvector。
2. 增加依赖、迁移和知识表。
3. 实现 Embedding Provider 和索引构建命令。
4. 实现混合 Retriever 和 30 条召回评测。
5. 定义 AgentState、节点和条件路由。
6. 接入 PostgreSQL checkpointer 和 execution 幂等。
7. 将 Responses SQL/总结 Adapter 接入图节点。
8. 串联 SSE 节点事件、取消和错误状态。
9. 跑完整测试、真实模型核心评测和 Code Review。

## 范围控制

- 不做开放式多 Agent、无限 ReAct 或模型任意工具调用。
- 不索引经营事实明细，业务结果仍由只读 SQL 实时查询。
- 不同时维护 pgvector 和第二套向量数据库。
- LangSmith 可后续接入，本轮以现有日志、执行步骤和测试报告完成审计。
