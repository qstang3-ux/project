# 后端代码规则

本文件适用于 `backend/`。同时遵循仓库根目录 `AGENTS.md`。

开始任何后端任务前，必须完整阅读：

1. `backend/README.md`
2. `backend/docs/HANDOFF.md`
3. `backend/docs/requirements.md`
4. `backend/docs/api/openapi.yaml`
5. `backend/docs/api/error-codes.md`
6. `backend/docs/data/metric-definitions.md`
7. `backend/docs/data/data-dictionary.md`
8. `backend/docs/data/database-design.md`
9. `backend/docs/data/seed-spec.md`
10. `backend/docs/text2sql/text2sql-design.md`
11. `backend/docs/text2sql/sql-security-policy.md`
12. `backend/docs/text2sql/model-integration.md`
13. `docs/00-shared/product-scope.md`
14. `docs/00-shared/acceptance-criteria.md`
15. `docs/00-shared/architecture.md`
16. `docs/00-shared/test-plan.md`
17. `docs/00-shared/deployment-design.md`
18. `docs/01-project-management/backlog.md`

## 1. 技术基线

- Python 3.12。
- FastAPI + Pydantic。
- SQLAlchemy 2.x + Alembic。
- PostgreSQL。
- sqlglot 解析和校验 SQL。
- Pytest、Ruff、MyPy。

## 2. 目录职责

```text
app/
├── api/           路由、依赖和 HTTP 映射
├── core/          配置、日志、异常和安全基础设施
├── models/        SQLAlchemy 模型
├── schemas/       Pydantic 输入输出模型
├── repositories/  平台数据持久化
├── services/      业务用例
└── text2sql/      召回、模型、校验、执行、总结
```

- API 路由只负责校验、调用 Service 和映射响应。
- Repository 不包含业务决策。
- Service 不依赖 FastAPI Request/Response。
- LLM Adapter 不访问数据库。
- Query Executor 不调用模型，也不能跳过 Validator。
- 所有后端实现、测试、迁移、Seed、评测和后端部署文件必须留在 `backend/`；不得在仓库根目录或 `frontend/` 新增后端业务文件。
- 后端可以更新其拥有的 OpenAPI，但不得修改前端业务实现；契约变更必须在最终报告中单列，供前端同步生成类型。

## 3. Python 规则

- 所有公共函数和方法使用类型标注。
- Pydantic 模型定义 API 边界，不直接暴露 ORM 对象。
- 不使用可变默认参数。
- 不使用裸 `except`，异常必须分类处理。
- 不在 import 时建立网络或数据库连接。
- 阻塞调用不得直接运行在异步事件循环中；同一调用链保持明确的同步或异步策略。
- 复杂函数超过约 60 行时优先拆分。
- 金额使用 Decimal/数据库 numeric，不使用 float。
- 时间保存 UTC，业务统计显式使用 Asia/Shanghai。

## 4. API 规则

- API 前缀 `/api/v1`。
- 请求和响应必须符合 OpenAPI。
- 错误使用统一结构和稳定错误码。
- 每个请求包含 Request ID。
- 列表接口使用统一分页结构。
- 创建查询、重新提交和重新生成使用幂等键。
- 外部错误对用户脱敏，完整异常只进入受控服务日志。

## 5. 数据库规则

- 数据库变更必须通过 Alembic，禁止仅手工修改数据库。
- 平台业务使用 `app` Schema，经营分析使用 `mart` Schema。
- Text2SQL 只能使用专用只读连接。
- 查询必须设置超时、行数上限和返回体限制。
- 金额、外键、唯一性和状态枚举应由数据库约束保护。
- Seed 使用固定种子并保持幂等。
- 破坏性迁移必须提供回滚或恢复说明。

## 6. Text2SQL 强制规则

- 模型输出一律视为不可信。
- 只允许单条 SELECT 或只读 CTE。
- 必须使用 AST 校验，正则只能作为附加检查。
- 必须校验 Schema、表、列和函数白名单。
- 禁止访问 `app`、`pg_catalog` 和 `information_schema`。
- 禁止 DDL、DML、事务、COPY、CALL、文件和网络函数。
- 自动添加或缩小 LIMIT。
- 安全拒绝不得通过自动纠错绕过。
- 每次纠错后的 SQL 必须重新完整校验。
- Fake Adapter 和真实 Adapter 必须经过完全相同的校验与执行路径。
- 禁止通过匹配问题直接返回固定业务答案。

## 7. 模型与密钥

- 模型供应商差异封装在 Adapter。
- API Key 只能来自 Secret、环境变量或加密存储。
- 响应和日志只允许密钥掩码。
- 模型调用必须设置超时和有限重试。
- 保存模型名、耗时、Token 和状态，不保存思维链。

## 8. 测试与命令

项目应提供并保持以下命令可用：

```text
ruff check .
ruff format --check .
mypy app
pytest
alembic upgrade head
```

SQL Validator 必须重点覆盖：

- 多语句。
- DDL/DML。
- 白名单外表。
- 系统 Schema。
- 注释和 Prompt Injection 绕过。
- LIMIT 改写。
- 只读 CTE。
- 超时和大结果集。

接口测试使用 Fake Adapter，不在 CI 调用付费模型。
