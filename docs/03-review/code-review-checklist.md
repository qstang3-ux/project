# 代码 Review 检查表

开始 Review 前先用项目地图建立整体心智模型：

- [前端 Code Review 可视化项目地图](../../frontend/docs/code-review-map.md)
- [后端 Code Review 可视化项目地图](../../backend/docs/code-review-map.md)
- [数据库 Code Review 可视化地图](../../backend/docs/data/schema-review-map.md)

## 数据模型与迁移

- [ ] `app` 平台数据与 `mart` 经营数据职责隔离。
- [ ] ORM 模型、Alembic head 和实际数据库结构一致。
- [ ] 会话、消息、执行、步骤、事件、回答版本和反馈血缘可追溯。
- [ ] checkpoint、副作用账本和持久事件分别承担恢复、幂等和通知职责。
- [ ] Text2SQL 查询账号只能读取授权的 `mart` 语义视图。
- [ ] 数据库变更具有迁移、Seed 验证和必要的回滚说明。

## 架构与契约

- [ ] OpenAPI 是前后端唯一接口契约。
- [ ] API、Service、Repository/Text2SQL 边界清楚。
- [ ] 前端通过统一 API Client 请求后端。
- [ ] 前后端业务代码和文档位于各自目录。

## Agent 与数据安全

- [ ] LLM 不直接访问数据库。
- [ ] 模型 SQL 经过 AST 校验、对象白名单和只读执行器。
- [ ] `app`、系统 Schema、DDL、DML、多语句和危险函数被阻断。
- [ ] Prompt、历史、RAG 和数据库错误按不可信数据处理。
- [ ] API Key 不进入前端、响应、普通日志或仓库。
- [ ] 模型不可用时失败关闭，不回退 Fake 冒充结果。

## 状态与可靠性

- [ ] 查询、澄清、重发和重新生成使用幂等键。
- [ ] 澄清最多两轮且复用 execution/checkpoint。
- [ ] 执行有 deadline、模型调用预算和 HTTP attempt 预算。
- [ ] queued/running 支持租约恢复，终态使用条件更新。
- [ ] SSE 支持 Last-Event-ID、过期游标和轮询降级。
- [ ] 回答版本链不会混入同会话无关执行。

## 前端体验

- [ ] Loading、空状态、失败、安全拒绝和等待补充状态清楚。
- [ ] 键盘操作、图标 aria-label 和弹窗保护可用。
- [ ] 表格、日志、设置页不存在双重滚动。
- [ ] 图表异常时保留表格。
- [ ] CSV、PNG 文件名和编码正确。

## 交付

- [ ] Lint、类型检查、单测、E2E 和生产构建通过。
- [ ] 迁移、Seed、RAG 索引和真实模型报告可复现。
- [ ] Compose 不包含真实密钥，Nginx SSE 关闭缓冲。
- [ ] 已知限制在 Review 报告中明确说明。
