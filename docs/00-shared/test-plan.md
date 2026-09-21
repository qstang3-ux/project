# 测试计划 v1.0

## 门禁

- 前端：ESLint、TypeScript、Vitest、React Testing Library、Playwright、生产构建。
- 后端：Ruff、MyPy、Pytest、迁移检查。
- 合并前单元/集成测试；发布前 E2E、评测、安全和 Docker 冒烟。

## 覆盖

- 后端：SQL Validator 100% 分支目标；服务层 ≥85%；整体 ≥80%。
- 前端：核心状态和交互，不以纯展示行覆盖率代替业务验证。
- 契约：OpenAPI 校验及生成类型无差异。

## 测试集

- 单元：口径、LangGraph 节点/路由、上下文裁剪、Schema 召回、SQL 校验/改写、格式化、状态机。
- 集成：数据库、会话、模型 Fake、SSE 顺序、反馈并发；Fake 用例只验证确定性工程链路。
- Agent 集成：PostgreSQL checkpointer、节点恢复、幂等执行、取消、安全拒绝和一次纠错上限。
- RAG 集成：pgvector 扩展、迁移、幂等入库、cosine Top-K、元数据过滤、混合召回和内容哈希更新。
- 真实模型冒烟：使用运行时 Secret 调用真实 OpenAI-compatible 服务，覆盖 SQL 生成、只读执行、一次纠错、结果总结和审计；不在普通 CI 中使用付费密钥。
- E2E：[验收标准](acceptance-criteria.md)中的全部场景。
- 安全：多语句、DDL/DML、系统表、Prompt injection、XSS、密钥脱敏。
- 性能：20 并发问数；CRUD P95<500ms，问数平均<8s（外部模型环境单独报告）。
- 兼容：最新版 Chrome/Edge，1280×720 和 1440×900。

缺陷发布门槛：S0/S1/S2=0；测试报告记录模型、数据版本、Seed 和时间。

发布报告必须明确区分 Fake、Mock 与真实模型结果。没有真实供应商调用证据时，真实 Agent 验收不得标记通过。

RAG 评测至少记录 Recall@5、MRR、索引文档数、Embedding 模型/维度、构建时间和单次召回耗时。安全测试必须验证知识文档不能通过 Prompt Injection 改写系统规则。
