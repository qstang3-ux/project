# 真实模型 Agent 交付计划

## 目标

将“Fake SQL 生成 + 真实数据库 + 固定回答模板”升级为可审计、可测试、失败关闭的真实模型 Agent 主链路。Fake Adapter 保留给单元测试、CI 和显式本地离线开发，但不作为受控运行环境的降级方案。

模型通过 OpenAI-compatible API 接入。API Key 仅在运行时配置或加密存储，不写入本文件或仓库。

Agent 编排改用 LangGraph Typed StateGraph，知识检索改用 pgvector + 中文 Embedding + 关键词的混合 RAG。详细节点、数据模型和验收见 [LangGraph 与向量 RAG 计划](langgraph-vector-rag-plan.md)。

## P0 工作包

### RA-01 运行模式与配置门禁

- 增加明确的模型运行模式，区分 `fake` 与 `real`。
- `demo`、`prod` 禁止选择 Fake；无可用真实模型时返回 `MODEL_NOT_CONFIGURED`。
- API Key 只从运行时 Secret、环境变量或加密存储读取。
- 启动日志只记录供应商、模型和掩码，不记录密钥。

### RA-02 结构化 SQL Agent

- 输入：规范化问题、最近上下文、召回后的 Schema、指标口径、数据截止日和安全规则。
- 输出：`intent`、`assumptions`、`sql`、`selectedObjects` 的严格 JSON。
- 对非法 JSON、缺字段、未知对象和超长输出分类报错。
- 候选 SQL 无条件进入 AST Validator；模型不能直接访问数据库。
- Adapter 必须支持 Responses API，不能假设所有模型都支持 `/chat/completions`。
- 连接测试必须同时校验 HTTP 状态、Content-Type 和协议响应结构；HTTP 200 HTML 不得判定为成功。

### RA-03 一次受控纠错

- 仅语法、列名和类型类错误允许一次纠错。
- 只向模型发送脱敏错误、原 SQL 和必要 Schema。
- 安全拒绝、权限失败、超时不得纠错。
- 纠错 SQL 重新通过完整 AST 校验后才能执行。

### RA-04 结果总结 Agent

- 输入仅包含问题、指标说明、列定义、行数、截断标记和受限结果 JSON。
- 输出严格 JSON：`answer`、`chart`、`followUpQuestions`。
- 后端核验答案关键数字存在于结果、图表字段存在于列、图表类型在白名单、追问不超过 3 条。
- 核验失败时返回明确错误或安全的程序化降级说明，不把未经验证内容展示给用户。

### RA-05 可观测与审计

- 分别记录 SQL 生成、纠错、结果总结调用的供应商、模型、耗时、Token、重试次数和状态。
- 贯穿 Request ID、execution ID 和模型配置 ID。
- 不保存思维链、密钥、Authorization Header 或未经脱敏的供应商错误体。

### RA-06 验证

- 单元测试：Prompt、结构化解析、重试、超时、429/5xx、鉴权、非法 JSON、输出核验。
- 集成测试：Fake + PostgreSQL 确定性链路，不调用付费模型。
- 真实冒烟：通过显式环境变量运行，覆盖 8 条核心评测问题和危险请求。
- 评测报告：记录模型名、Seed `20260915`、数据截止日 `2026-05-31`、执行 ID、Token、耗时、SQL 与结果正确性。

## 推荐实现顺序

1. 运行模式门禁和配置加载。
2. 抽象 SQL 生成与结果总结两个模型能力。
3. 完成结构化输出解析和校验。
4. 接入一次受控纠错。
5. 补齐审计字段和日志。
6. 编写真实模型冒烟脚本。
7. 使用真实配置运行 8 条核心评测问题。
8. 前后端真实联调和 Code Review。

## 完成标准

- 受控运行环境的执行记录显示真实供应商模型名，不出现 `fake-deterministic-v1`。
- 8 条核心评测问题全部经过真实模型、Validator 和只读 PostgreSQL。
- 危险 SQL 拦截率 100%，模型不可绕过校验器。
- 回答、图表和追问来自真实模型结构化输出并通过程序核验。
- 真实冒烟报告与 Fake/Mock 自动化测试报告分开。
- Ruff、格式检查、MyPy、Pytest、迁移和前后端 E2E 全部通过。

## 外部依赖

真实冒烟需要用户或部署环境提供 OpenAI-compatible Base URL、模型名和 API Key。密钥不得写入仓库、文档、测试输出或普通日志。
