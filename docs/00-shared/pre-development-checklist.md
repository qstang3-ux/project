# 开发前准备检查表

| 项目 | 状态 | 依据 |
|---|---|---|
| MVP/排除范围 | 完成 | [产品范围](product-scope.md) |
| 历史原型交互审计 | 完成 | 已归档至 `docs/DEMONSTRATION.md` |
| 前端需求 | 完成 | [前端需求](../../frontend/docs/requirements.md) |
| 后端需求 | 完成 | [后端需求](../../backend/docs/requirements.md) |
| 验收标准 | 完成 | [验收标准](acceptance-criteria.md) |
| 业务指标口径 | 完成 | [指标口径](../../backend/docs/data/metric-definitions.md) |
| 历史原型字段提取与映射 | 完成 | 已归档至 `docs/DEMONSTRATION.md` |
| 数据模型/字典 | 完成 | [数据库设计](../../backend/docs/data/database-design.md)、[数据字典](../../backend/docs/data/data-dictionary.md) |
| 初版 DDL | 完成 | [schema.sql](../../backend/data/schema.sql) |
| Seed 数据规格 | 完成 | [seed-spec.md](../../backend/docs/data/seed-spec.md) |
| 架构和模块边界 | 完成 | [系统架构](architecture.md) |
| Text2SQL 方案 | 完成 | [Text2SQL 设计](../../backend/docs/text2sql/text2sql-design.md) |
| SQL 安全策略 | 完成 | [SQL 安全策略](../../backend/docs/text2sql/sql-security-policy.md) |
| 模型接入策略 | 完成 | [模型接入](../../backend/docs/text2sql/model-integration.md) |
| API 字段级契约 | 完成 | [OpenAPI](../../backend/docs/api/openapi.yaml)、[错误码](../../backend/docs/api/error-codes.md)；已覆盖请求、响应、分页、SSE、错误和核心枚举 |
| 前端组件/状态设计 | 完成 | [前端设计](../../frontend/docs/design.md)、[UI 基线](../../frontend/docs/ui-design-system.md) |
| 测试计划 | 完成 | [测试计划](test-plan.md) |
| Text2SQL 30题评测集 | 完成 | [评测集](../../backend/tests/evaluation/text2sql-cases.json) |
| 项目 Backlog | 完成 | [Backlog](../01-project-management/backlog.md) |
| 开发与变更流程 | 完成 | [开发流程](../01-project-management/development-process.md) |
| 环境变量契约 | 完成 | [.env.example](../../.env.example) |
| Docker/Linux 设计 | 完成 | [部署设计](deployment-design.md) |
| 决策和假设 | 完成 | [决策日志](../01-project-management/decision-log.md) |

## Ready Gate 结论

规格层面具备开发准入条件。OpenAPI 已形成可生成前端类型的字段级契约；实现时先从契约生成类型，再编码，不允许前后端各自猜字段。后端如需改变字段，必须先更新契约并在交付报告中列出，前端随后重新生成类型。

尚未完成的事项均属于开发工作而非开发前准备：工程脚手架、迁移实现、Seed 生成器、API/页面、自动化测试代码、Dockerfile/Compose 和 CI。
