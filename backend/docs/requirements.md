# 经管之星后端需求文档

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 项目名称 | 经管之星——企业经营数据智能问数平台 |
| 文档类型 | 后端产品与系统需求文档 |
| 版本 | v1.0 |
| 状态 | MVP 基线 |
| 技术约束 | Python |
| 推荐框架 | FastAPI + SQLAlchemy + Alembic |

## 2. 建设目标

后端负责业务数据管理、会话和配置持久化、模型调用、Text2SQL、SQL 安全控制、只读查询、答案生成、反馈闭环、审计日志以及 Docker/Linux 运行能力。

系统不实现登录和用户管理。为保留数据归属和审计能力，MVP 使用由后端配置注入的固定系统用户标识，不接受前端伪造管理员身份。

## 3. 系统边界

### 3.1 本期包含

- 数据源元数据管理。
- 固定经营验收数据。
- 问答会话与消息。
- Text2SQL 生成、校验、执行和总结。
- 问数流式进度。
- 常问与收藏问题。
- 模型配置。
- 应用配置。
- 回答反馈和回复校对。
- 问答执行日志。
- 测试、监控、Docker 部署。

### 3.2 本期不包含

- 登录、用户、角色和权限管理。
- 多租户。
- 数据写入型智能助手。
- 自由执行用户提供的 SQL。
- Excel 台账管理。
- 企业级高可用集群。
- 计费系统。

## 4. 总体架构要求

```text
React Web
   │ REST + SSE
   ▼
FastAPI
   ├── Session Service
   ├── Configuration Service
   ├── Feedback Service
   └── Text2SQL Orchestrator
          ├── Schema Retriever
          ├── LLM Adapter
          ├── SQL Validator
          ├── Read-only Executor
          ├── Result Analyzer
          └── Chart Recommender
   │
   ▼
PostgreSQL
```

MVP 可以让业务数据和平台数据位于同一 PostgreSQL 实例，但必须使用不同 Schema 或不同连接账号。Text2SQL 查询必须通过只读账号执行。

## 5. 技术和非功能需求

### BE-NFR-001 技术栈

- Python 3.12 或项目确定的稳定版本。
- FastAPI 提供 HTTP API。
- Pydantic 定义输入输出模型。
- SQLAlchemy 2.x 管理数据库访问。
- Alembic 管理数据库迁移。
- PostgreSQL 作为默认数据库。
- `sqlglot` 或等价 AST 工具解析 SQL。
- Pytest 作为测试框架。

### BE-NFR-002 API 规范

- API 前缀使用 `/api/v1`。
- 使用 JSON 作为默认数据格式。
- 流式问数使用 SSE。
- 列表接口统一支持分页。
- 时间统一存储为 UTC，并返回 ISO 8601 格式。
- OpenAPI 文档必须可访问。
- 所有错误采用统一结构。

建议错误结构：

```json
{
  "error": {
    "code": "SQL_VALIDATION_FAILED",
    "message": "生成的查询未通过安全校验",
    "requestId": "req_xxx",
    "details": null
  }
}
```

### BE-NFR-003 性能

- 普通 CRUD 接口 P95 响应时间小于 500ms，不包含外部模型调用。
- 核心问数请求目标平均完成时间小于 8 秒。
- SQL 默认超时 10 秒，可配置但最大不得超过 30 秒。
- 单次查询默认最大返回 500 行。
- 单次导出默认最大 10,000 行。
- 单个问题长度最大 2,000 字符。

### BE-NFR-004 可靠性

- 每个请求生成唯一 Request ID。
- 模型调用和 SQL 执行必须设置超时。
- 模型调用支持有限重试，默认最多 2 次。
- SQL 自动纠错默认最多 1 次，不得无限循环。
- 服务关闭时正确终止数据库连接和流式任务。
- 健康检查区分存活与就绪状态。

### BE-NFR-005 安全

- 模型密钥不得返回给前端。
- 模型密钥不得以明文写入日志。
- 正式环境密钥优先通过 Secret 或环境变量注入。
- 如必须持久化密钥，必须进行应用层加密。
- Text2SQL 使用只读数据库账号。
- 不信任模型生成的 SQL，必须经过 AST 校验。
- 禁止把数据库完整错误和堆栈返回前端。
- 日志中的问题和结果需要限制长度并支持敏感字段脱敏。

## 6. 数据需求

### BE-DATA-001 业务验收数据

验收数据至少覆盖：

- 2025、2026 两个年度。
- 不少于 20 个经营单元。
- 不少于 4 个行业。
- 3 个产品线。
- 年度、季度或月度经营目标。
- 不少于 1,000 条订单或收入明细。

数据必须使用固定随机种子或静态 Seed，重复初始化后查询结果一致。

### BE-DATA-002 推荐业务表

| 表 | 用途 |
|---|---|
| `business_units` | 经营单元 |
| `industries` | 行业维度 |
| `product_lines` | 产品线维度 |
| `customers` | 客户信息 |
| `sales_targets` | 年度、季度或月度目标 |
| `sales_orders` | 销售订单 |
| `sales_revenue` | 收入事实数据 |

所有业务表和字段必须具有中文业务说明、数据类型说明及可查询标识。

### BE-DATA-003 平台表

| 表 | 关键内容 |
|---|---|
| `data_sources` | 数据源名称、类型、状态、默认标记 |
| `qa_sessions` | 会话标题、置顶状态、更新时间 |
| `qa_messages` | 用户与助手消息 |
| `qa_executions` | 问题、SQL、状态、耗时、错误和模型 |
| `qa_execution_steps` | 可审计的执行步骤 |
| `favorite_questions` | 收藏问题 |
| `qa_feedback` | 用户反馈、原因、状态和处理备注 |
| `model_configs` | 模型连接配置及密钥引用 |
| `app_configs` | 应用配置 |

### BE-DATA-004 数据字典与指标口径

必须提供：

- 表中文名称和用途。
- 字段中文名称和含义。
- 表之间的 Join 关系。
- 可用时间字段。
- 可用聚合字段。
- 单位及币种。
- 商业目标、收入、完成率、同比、环比等指标定义。
- 指标适用范围和异常值说明。

这部分元数据必须能够被 Text2SQL Prompt 或 Schema 检索模块使用。

## 7. 数据源管理

### BE-DS-001 数据源列表

- 返回可用于问数的数据源。
- 字段包括 ID、名称、描述、状态、是否默认、数据更新时间。
- 不得返回数据库密码或连接串。
- MVP 至少提供一个默认经营数据源。

### BE-DS-002 数据源隔离

- Text2SQL 执行只能访问启用的数据源。
- 每个数据源配置允许查询的表白名单。
- 数据源不可用时返回明确错误码。

## 8. 会话与消息

### BE-QA-001 会话管理

支持：

- 创建会话。
- 分页查询会话。
- 查询会话详情。
- 修改标题。
- 置顶和取消置顶。
- 删除会话。

规则：

- 标题最大 60 字符。
- 新会话可使用“新对话”作为临时标题。
- 第一条问题提交后可自动生成标题。
- 删除会话采用软删除或级联清理，由设计文档明确。

### BE-QA-002 消息管理

- 消息角色包含 `user`、`assistant`、`system_event`。
- 用户消息必须关联一次问数执行。
- 助手消息记录回答正文、SQL、结果摘要和图表建议引用。
- 会话详情支持分页加载历史消息。
- 不允许前端直接写入助手消息。

### BE-QA-003 编辑重发与重新生成

- 编辑问题后重新发送不得覆盖或删除原消息、原回答和原执行记录。
- 编辑历史问题时创建会话分支或等价的可追踪版本关系。
- 新用户消息记录 `source_message_id`，用于关联被编辑的原始消息。
- 重新生成回答使用原问题、原数据源及当时有效上下文重新执行完整 Text2SQL 流程。
- 新执行记录通过 `regenerated_from_execution_id` 关联旧执行。
- 同一消息的多个回答版本均应保留，默认版本由业务状态字段标识。
- 请求进行中不允许对同一消息重复触发重新生成。
- 编辑、重发和重新生成均应产生独立审计记录。

## 9. Text2SQL 核心需求

### BE-T2S-001 输入

核心输入包括：

- 用户问题。
- 会话 ID。
- 数据源 ID 列表。
- 可选的上下文消息。
- 可选的请求参数，例如是否生成图表。

后端必须校验会话和数据源是否有效。

### BE-T2S-002 相关 Schema 选择

- 根据问题选择相关表、字段和指标定义。
- 不应在每次请求中把整个数据库 Schema 无限制发送给模型。
- 必须使用 pgvector 语义检索与关键词检索的混合召回；单一关键词规则不满足正式验收。
- 必须记录最终提供给模型的表名集合，便于审计。
- 向量知识类型包含 Schema、字段、指标、Join、口径和审核后的 Few-shot。
- 召回结果必须受数据源、知识类型和版本元数据过滤。

### BE-T2S-003 SQL 生成

- Prompt 包含数据库类型、相关 Schema、Join 关系、指标口径、安全约束和 Few-shot 示例。
- 模型输出必须采用可解析的结构化格式。
- SQL 生成和答案总结可以使用同一个模型，也可以配置不同模型。
- 不保存模型完整内部思维过程，只保存必要的执行摘要。
- `demo` 和 `prod` 必须调用已配置的真实模型，禁止使用固定问题映射生成 SQL 冒充真实 Text2SQL。

### BE-T2S-004 SQL 安全校验

生成 SQL 在执行前必须满足：

- 只能包含单条查询语句。
- 只允许 `SELECT` 或只读 CTE。
- 禁止 DDL、DML、事务控制和管理语句。
- 禁止注释中隐藏额外语句。
- 禁止访问白名单外的表和 Schema。
- 禁止调用高风险数据库函数。
- 禁止无限制笛卡尔积。
- 自动应用行数限制。
- 解析失败时禁止执行。

禁止项至少包括：

```text
INSERT UPDATE DELETE MERGE
DROP ALTER CREATE TRUNCATE
GRANT REVOKE
COPY CALL EXECUTE
SET RESET
```

校验必须基于 AST，不得只依赖关键字正则表达式。

### BE-T2S-005 SQL 执行

- 使用专用只读连接。
- 设置事务只读模式。
- 设置查询超时。
- 限制返回行数和返回体大小。
- 记录开始时间、结束时间、行数和状态。
- 执行失败时生成脱敏错误摘要。
- 不向模型提供数据库密码或连接信息。

### BE-T2S-006 自动纠错

- 仅对可恢复的语法、字段或类型错误触发纠错。
- 将脱敏后的数据库错误、原 SQL 和相关 Schema 提供给模型。
- 默认最多纠错一次。
- 每次纠错必须重新进行完整安全校验。
- 权限错误、超时和安全拒绝不得通过纠错绕过。

### BE-T2S-007 结果分析

- 根据查询结果生成简洁的自然语言结论。
- 不得编造结果中不存在的数字。
- 空结果需要明确说明未查询到数据。
- 结果被截断时必须告知模型和用户。
- 大结果集仅使用安全摘要生成答案。
- 演示和生产环境必须调用真实模型生成结果结论；固定模板只允许作为模型不可用时的明确错误说明，不得冒充模型总结。
- 回答生成后必须程序化核验关键数字、截断声明和引用字段。

### BE-T2S-008 图表建议

返回结构化图表配置，而不是任意前端代码。

MVP 支持：

- `bar`
- `line`
- `pie`
- `metric`
- `none`

建议结构：

```json
{
  "type": "bar",
  "title": "各经营单元商业目标",
  "xField": "经营单元",
  "yFields": ["商业目标"],
  "unit": "万元"
}
```

后端必须验证字段确实存在于结果集中。

### BE-T2S-009 推荐追问

- 最多返回 3 条。
- 推荐问题必须与当前数据源和查询结果相关。
- 应用配置关闭时不生成。
- 不得推荐明显无法由当前数据源回答的问题。

### BE-T2S-010 流式事件

SSE 至少包含：

| 事件 | 含义 |
|---|---|
| `execution.started` | 执行开始 |
| `schema.selected` | 完成表和字段选择 |
| `sql.generated` | SQL 已生成 |
| `sql.validated` | SQL 已通过安全校验 |
| `query.completed` | 数据库查询完成 |
| `answer.completed` | 回答生成完成 |
| `execution.failed` | 执行失败 |
| `execution.cancelled` | 用户取消 |

每个事件包含执行 ID、时间、状态及允许展示的摘要。

后端持久化的审计步骤为 Schema 选择、SQL 生成、SQL 安全校验、查询执行和回答生成。
“分析问题”和“已完成”属于前端展示的执行生命周期状态，分别由 `execution.started` 和
执行状态表达，不作为额外的数据库审计步骤。事件 `data` 使用按 `kind` 判别的结构化负载。
执行详情必须提供结构化 SQL 校验状态，不能要求调用方从步骤摘要文案推断。

### BE-T2S-011 取消执行

- 用户可以取消仍在运行的问数请求。
- 后端应尽可能取消模型请求和数据库查询。
- 已完成的执行返回幂等结果。
- 取消状态必须写入执行日志。

### BE-T2S-012 回答版本

- 每次重新生成产生新的助手消息或回答版本，不能覆盖旧版本。
- 查询执行详情时可以获取版本列表及当前展示版本。
- 回答版本至少记录模型、SQL、查询结果摘要、生成时间和执行耗时。
- 切换当前展示版本不得改变底层查询历史。

### BE-T2S-013 LangGraph 编排

- 使用 Typed StateGraph 显式定义节点输入输出和条件边。
- 现有 Schema Retriever、模型 Adapter、SQL Validator、只读 Executor 和回答核验保持独立服务并作为节点调用。
- 每个 execution 映射唯一 graph thread/checkpoint 标识。
- 图必须支持节点进度、取消、安全拒绝、一次纠错、失败终态和中断恢复。
- 图版本写入执行审计，升级图结构不得破坏历史执行记录。
- 禁止无限 ReAct 循环和模型自由调用未注册工具。

### BE-T2S-014 向量知识库

- PostgreSQL 启用 `vector` 扩展；知识表位于 `app` Schema，不向 Text2SQL 只读账号授权。
- 默认 Embedding 为 `BAAI/bge-small-zh-v1.5`，512 维并归一化。
- 文档使用稳定 ID、内容哈希、知识类型、来源、版本和更新时间实现幂等更新。
- 默认 cosine Top-K 检索；知识规模小时允许精确搜索，达到阈值后使用 HNSW。
- Embedding 或 pgvector 不可用时，`demo`/`prod` 失败关闭；显式 local 模式才允许关键词降级并记录 degraded。

## 10. 模型配置

### BE-MODEL-001 配置管理

模型配置字段至少包括：

- 配置名称，1～50 字符。
- 供应商。
- Base URL。
- 模型名称，1～100 字符。
- 密钥加密值或 Secret 引用。
- 请求超时。
- 是否启用。
- 是否为当前模型。
- 创建和更新时间。

API 返回时只允许提供密钥掩码，不返回密钥原文。

### BE-MODEL-002 OpenAI 兼容层

- MVP 优先支持 OpenAI 兼容 Chat Completions 或 Responses 风格接口之一。
- 模型适配层必须隔离供应商差异。
- 业务服务不得直接依赖某一供应商 SDK。
- 模型调用记录供应商、模型、耗时、状态和 Token 用量。

### BE-MODEL-003 连接测试

- 使用最小请求验证 Base URL、模型名和密钥。
- 设置较短超时。
- 返回成功、超时、鉴权失败、模型不存在等脱敏结果。
- 测试请求不得写入正式问答会话。

### BE-MODEL-004 当前模型

- 同一用途最多有一个当前启用模型。
- 切换操作必须具备事务一致性。
- 当前模型不可直接删除。
- 没有可用模型时，问数接口返回明确业务错误。

### BE-MODEL-005 环境隔离与失败关闭

- Fake Adapter 仅允许用于单元测试、CI 和显式本地离线开发。
- `demo`、`prod` 启动或执行问数时必须验证存在可用真实模型。
- 真实模型不可用时返回脱敏错误，不得静默回退 Fake。
- 每次真实调用记录供应商、模型、用途、耗时、Token、重试次数、状态和 Request ID。

## 11. 应用配置

### BE-APP-001 配置项

- 开场白开关及文本。
- 推荐问题列表，最多 10 条，单条 1～100 字符。
- 推荐追问开关。
- 常问问题开关。
- 常问统计阈值。
- 模型问数开关。
- TTS/STT 预留开关。

### BE-APP-002 配置规则

- 提供查询和更新接口。
- 更新时进行完整字段校验。
- 使用版本号或更新时间支持并发修改检测。
- 配置变更记录操作时间和固定系统用户标识。

## 12. 常问与收藏

### BE-QQ-001 常问问题

- 根据标准化后的问题文本统计出现次数。
- 达到应用配置阈值后进入常问列表。
- 支持限制统计时间范围，例如近 30 天。
- 默认最多返回 20 条。
- 不统计失败、取消或明显无效问题，可配置。

### BE-QQ-002 收藏问题

- 支持收藏、取消收藏和查询收藏列表。
- 同一用户标识下相同标准化问题不得重复收藏。
- 收藏操作必须幂等。

## 13. 反馈与回复校对

### BE-FB-001 提交反馈

反馈必须关联：

- 会话 ID。
- 助手消息 ID。
- 执行记录 ID。
- 用户问题。
- 用户选择的反馈原因。
- 可选补充说明，最多 500 字符。

后端通过关联记录获取 SQL、结果和回答，不信任前端重复上传的快照。

### BE-FB-002 反馈状态

状态包括：

- `pending`：待处理。
- `processing`：处理中。
- `resolved`：已解决。
- `ignored`：已忽略。

### BE-FB-003 回复校对

- 支持按关键词、固定用户标识、状态、原因和时间分页查询。
- 详情包含问题、SQL、数据源、结果摘要、模型和回答。
- 支持更新状态和处理备注。
- 处理备注最大 2,000 字符。
- 使用版本字段或更新时间处理并发更新冲突。

## 14. 问答日志与审计

### BE-LOG-001 执行日志

每次问数记录：

- Request ID 和执行 ID。
- 会话及消息 ID。
- 用户问题。
- 数据源。
- 选中的表。
- 生成和最终执行的 SQL。
- 安全校验结果。
- 查询行数。
- 模型和 Token 用量。
- 各阶段耗时。
- 执行状态。
- 脱敏后的错误信息。

### BE-LOG-002 日志查询

- 支持按时间、固定用户标识、状态、问题关键词和模型筛选。
- 支持分页和详情查询。
- API Key、数据库密码和连接串必须脱敏。
- 生产日志与数据库审计记录应具有合理保留期限。

## 15. API 需求清单

以下为建议接口，最终字段以 OpenAPI 为准。

### 数据源

```text
GET    /api/v1/data-sources
```

### 会话与消息

```text
POST   /api/v1/qa/sessions
GET    /api/v1/qa/sessions
GET    /api/v1/qa/sessions/{sessionId}
PATCH  /api/v1/qa/sessions/{sessionId}
DELETE /api/v1/qa/sessions/{sessionId}
GET    /api/v1/qa/sessions/{sessionId}/messages
POST   /api/v1/qa/sessions/{sessionId}/queries
POST   /api/v1/qa/messages/{messageId}/resubmit
POST   /api/v1/qa/messages/{messageId}/regenerate
GET    /api/v1/qa/messages/{messageId}/versions
GET    /api/v1/qa/executions/{executionId}/events
POST   /api/v1/qa/executions/{executionId}/cancel
GET    /api/v1/qa/executions/{executionId}
GET    /api/v1/qa/executions/{executionId}/export
```

`POST /queries` 可以返回执行 ID，再由 SSE 接口订阅事件；也可以直接建立 SSE，具体方式需在 API 设计阶段固定。

### 常问与收藏

```text
GET    /api/v1/questions/frequent
GET    /api/v1/questions/favorites
POST   /api/v1/questions/favorites
DELETE /api/v1/questions/favorites/{favoriteId}
```

### 模型配置

```text
GET    /api/v1/model-configs
POST   /api/v1/model-configs
GET    /api/v1/model-configs/{id}
PATCH  /api/v1/model-configs/{id}
DELETE /api/v1/model-configs/{id}
POST   /api/v1/model-configs/test
POST   /api/v1/model-configs/{id}/activate
```

### 应用配置

```text
GET    /api/v1/application-config
PUT    /api/v1/application-config
```

### 反馈

```text
POST   /api/v1/feedback
GET    /api/v1/feedback
GET    /api/v1/feedback/{id}
PATCH  /api/v1/feedback/{id}
```

### 日志与健康检查

```text
GET    /api/v1/qa/logs
GET    /api/v1/qa/logs/{executionId}
GET    /health/live
GET    /health/ready
```

## 16. 状态码及幂等性

- 创建成功使用 201。
- 查询成功使用 200。
- 无响应体删除可使用 204。
- 参数校验失败使用 422。
- 资源不存在使用 404。
- 并发或当前模型删除冲突使用 409。
- 请求过于频繁使用 429。
- 外部模型不可用可映射为 502 或明确业务错误。
- 模型超时和数据库超时可使用 504 或明确业务错误。
- 收藏、取消收藏和取消执行必须具备幂等性。
- 重发和重新生成接口必须接受幂等键，避免重复创建执行记录。

## 17. 测试要求

### BE-TEST-001 单元测试

重点覆盖：

- Prompt 组装。
- Schema 选择。
- SQL AST 校验。
- 表白名单。
- 自动行数限制。
- SQL 错误分类。
- 图表字段验证。
- 配置和反馈校验。

### BE-TEST-002 集成测试

- 数据库迁移和 Seed。
- 会话及消息 CRUD。
- 模型连接测试 Mock。
- Text2SQL 完整链路。
- SQL 超时与取消。
- 反馈提交和处理。
- SSE 事件顺序。

### BE-TEST-003 安全测试

至少覆盖：

- 多语句攻击。
- 注释绕过。
- DDL/DML。
- 白名单外表访问。
- 高风险函数。
- Prompt Injection 要求泄露 Schema 或执行写操作。
- 超大结果集。
- 超长输入。
- API Key 日志泄露。

### BE-TEST-004 Text2SQL 评测

建立不少于 30 个固定问题，包含：

- 简单筛选。
- 聚合。
- Top N。
- 时间范围。
- 同比和环比。
- 多表关联。
- 空结果。
- 模糊问题。
- 越权或危险请求。

MVP 目标：

| 指标 | 目标 |
|---|---:|
| SQL 可执行率 | ≥95% |
| 核心问题结果正确率 | ≥90% |
| 核心评测问题成功率 | 100% |
| 危险 SQL 拦截率 | 100% |

### BE-TEST-005 真实模型冒烟

- 使用运行时 Secret 调用真实 OpenAI-compatible 服务，不提交密钥。
- 至少覆盖 8 条核心评测问题、一次可恢复纠错、危险 SQL 拒绝、超时/鉴权/非法 JSON。
- 报告记录模型名、执行 ID、Token、耗时、SQL 校验状态和结果正确性。
- Fake/Mock 结果必须单独标记，不能计入真实模型冒烟通过数。

### BE-TEST-006 LangGraph 与 RAG

- 覆盖每个节点、条件边、一次纠错上限、checkpoint 恢复、取消和幂等。
- 30 条问题记录 RAG Top-5，正确 Schema/指标 Recall@5 必须为 100%。
- 覆盖向量扩展不可用、Embedding 下载/加载失败、知识版本更新和 Prompt Injection 文档。
- 检查 RAG 表、checkpoint 表和模型调用日志均不包含 API Key 或数据库连接串。

## 18. 日志、监控和运维

- 使用结构化日志。
- 日志至少包含时间、级别、服务名、Request ID 和事件名。
- 暴露存活和就绪检查。
- 记录 HTTP 请求量、错误率、响应时间。
- 记录模型调用次数、耗时、错误率和 Token。
- 记录 SQL 执行次数、耗时、超时和拒绝次数。
- 不把完整查询结果写入普通运行日志。

## 19. Docker/Linux 部署

- 提供后端 Dockerfile。
- 使用非 root 用户运行服务。
- 通过环境变量注入配置。
- 容器启动时不得自动执行破坏性数据重置。
- 数据库迁移和 Seed 使用明确的独立命令。
- 提供 Docker Compose，至少包含 frontend、backend、postgres。
- 正式镜像固定依赖版本。
- 支持在 Linux x86_64 环境启动。

必要环境变量至少包括：

```text
APP_ENV
DATABASE_URL
QUERY_DATABASE_URL
MODEL_SECRET_KEY
DEFAULT_MODEL_CONFIG
LOG_LEVEL
SQL_TIMEOUT_SECONDS
SQL_MAX_ROWS
```

实际 `.env` 不得提交版本库，只提交 `.env.example`。

## 20. 后端交付和验收

交付物：

- Python 后端源代码。
- OpenAPI 文档。
- SQLAlchemy 模型和 Alembic 迁移。
- 固定 Seed 数据。
- 数据字典和指标口径。
- Text2SQL 与 SQL 安全实现。
- 自动化测试及评测集。
- Dockerfile 和运行说明。
- 部署、运维和安全说明。

后端整体完成标准：

- 核心问数链路使用真实数据库和真实模型。
- 所有 SQL 在执行前经过 AST 安全校验。
- 查询账号为只读。
- 模型密钥未暴露给前端或日志。
- API、迁移、测试和 Docker 启动均通过。
- Text2SQL 评测达到本文目标。
- 核心评测问题能够稳定重复执行并得到一致结果。
