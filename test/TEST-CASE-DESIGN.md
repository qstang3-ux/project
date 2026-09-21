# 经管之星 Agent 平台测试用例设计

版本：v1.0  
日期：2026-09-20  
状态：待评审 / 尚未执行

## 1. 测试目标

验证“经管之星”从自然语言提问到只读 SQL、数据查询、答案总结、图表、追问、反馈及审计的完整链路，覆盖前端、后端、Agent、RAG、数据口径、安全、恢复能力和真实用户体验。

## 2. 测试依据

- `docs/00-shared/product-scope.md`
- `docs/00-shared/acceptance-criteria.md`
- `docs/00-shared/test-plan.md`
- `frontend/docs/requirements.md`
- `backend/docs/requirements.md`
- `backend/docs/api/openapi.yaml`
- `backend/docs/text2sql/sql-security-policy.md`
- `backend/docs/data/metric-definitions.md`
- `backend/docs/data/seed-spec.md`
- `backend/tests/evaluation/*.json`

## 3. 范围与分层

| 测试域 | 重点 |
|---|---|
| 核心用户旅程 | 8 条验收场景、会话、追问、编辑重发、重新生成、反馈闭环 |
| 前端与体验 | 状态展示、输入/键盘、表格/图表、导出、语音、响应式、无障碍、错误恢复 |
| API 与后端 | OpenAPI、分页、幂等、并发控制、错误结构、Request ID、健康检查 |
| Agent 与 RAG | 图节点、澄清、上下文、一次纠错、checkpoint、真实模型、召回质量 |
| 数据与口径 | 固定 Seed、金额/比例/时间口径、空值与零值、结果一致性 |
| 安全 | SQL AST、对象/函数白名单、Prompt Injection、XSS、密钥与错误脱敏 |
| 非功能与部署 | 性能、兼容、断线/取消、Docker、迁移、Seed 幂等、质量门禁 |

## 4. 执行原则

1. Mock、Fake、真实模型的结果必须分别记录，不可互相替代。
2. 真实 Agent 验收必须保存供应商、模型名、执行 ID、Token、耗时和脱敏状态证据。
3. 业务结果测试使用固定 Seed `20260915`，数据版本为 `seed-20260915`，分析截止日为 `2026-05-31`。
4. 同一核心问题至少核对 SQL 安全性、结果集、答案关键数字、图表字段和审计日志五类证据。
5. 所有安全拒绝均需确认 SQL 未进入执行器，且不能由纠错分支绕过。
6. 缺陷严重度采用 S0（灾难）、S1（阻断）、S2（严重）、S3（一般）、S4（建议）。发布门槛为 S0/S1/S2 = 0。
7. 工作簿中的“执行状态、实际结果、证据链接、缺陷 ID”由测试执行阶段填写。

## 5. 环境矩阵

| 环境 | 用途 | 模型模式 | 数据 |
|---|---|---|---|
| 单元/CI | 逻辑、组件、契约和安全规则 | Mock/Fake | 隔离夹具 |
| 本地集成 | API、PostgreSQL、SSE、恢复、E2E | Fake + 可选真实模型 | 固定 Seed |
| 真实模型受控环境 | 真实 Agent、容错、Token/审计 | 真实 OpenAI-compatible | 固定 Seed |
| Docker 发布候选 | 部署、健康检查、Nginx SSE | 真实模型或明确受控配置 | 固定 Seed |

## 6. 准入条件

- OpenAPI、迁移、Seed 和前后端版本已确定。
- PostgreSQL/pgvector、只读查询账号和测试数据可用。
- 真实模型测试所需 Secret 通过运行时注入，不落盘、不进入前端。
- Chrome、Edge 及 1024×720、1280×720、1440×900 测试环境就绪。

## 7. 准出条件

- 8 条核心验收场景通过率 100%。
- 30 条 Text-to-SQL：SQL 可执行率 ≥95%，结果正确率 ≥90%。
- 30 条 RAG：Recall@5 = 100%，并记录 MRR、文档数、Embedding 版本/维度、构建与召回耗时。
- 危险 SQL 拦截率 100%，Prompt Injection 五类通道均无越权。
- 前端 lint/typecheck/test/build/e2e 与后端 ruff/mypy/pytest/迁移检查通过。
- 20 并发问数通过；CRUD P95 < 500ms，问数平均 < 8s，外部模型影响单列。
- S0/S1/S2 缺陷为 0；所有失败用例均有关联缺陷和复测结论。

## 8. 交付物

- `经管之星-Agent平台测试用例-v1.0.xlsx`：完整可执行用例、30 条 Agent 评测、30 条 RAG 评测、执行记录和缺陷跟踪模板。
- 本文档：测试范围、策略、门槛与执行约定。

## 9. 不在本轮范围

- 登录、用户、角色、权限、多租户。
- 驾驶舱、固定经营报表、台账导入编辑、审批流。
- 用户自由编辑并执行 SQL。
- 云端 STT/TTS 和实时语音对话。

