# SQL 安全策略 v1.0

## 强制规则

- 仅允许 PostgreSQL 单条 SELECT 或只读 CTE。
- 使用 sqlglot AST 解析；解析失败即拒绝。
- 只允许 `mart.v_sales_performance`、`mart.v_target_achievement`、`mart.v_pipeline_risk` 及批准的 mart 基础表。
- 禁止 `app`、`pg_catalog`、`information_schema`、跨库和未限定 Schema 对象。
- 禁止 DDL/DML、COPY、CALL、DO、SET、事务控制、文件/网络/系统函数。
- 禁止 `SELECT *`（仅 `count(*)` 例外）；禁止无连接条件的多表查询。
- 最外层自动施加 `LIMIT 500`；已有更大 LIMIT 改写为 500。
- 只读账号、只读事务、statement timeout 10s、锁等待 2s。
- 返回体最大 5MB；超限终止并返回错误。

## 防护顺序

规范化 → 单语句检查 → AST 类型 → 对象白名单 → 列/函数策略 → Join 检查 → LIMIT 改写 → EXPLAIN 成本阈值 → 只读执行。

## 审计

保存原始模型 SQL、改写后 SQL、拒绝原因和规则版本。安全拒绝不可被模型纠错绕过。

## 注入与错误通道

- 用户、历史消息、RAG 文档、查询结果和候选 SQL 都是数据，不是 SQL 安全策略来源。
- RAG 只能帮助选择已经由数据源授权且由程序召回的对象；文档内容不得扩展表、列、函数或 Schema。
- SQL 执行异常只按固定 SQLSTATE 映射为 `syntax_error`、`undefined_column`、`undefined_table`、
  `undefined_function`、`grouping_error`、`datatype_mismatch`、`cannot_coerce` 或
  `invalid_text_representation`。纠错模型不得接收数据库原始异常文本。
- 纠错输出重新执行完整 AST 校验，不能放宽首次查询的对象交集、只读约束、LIMIT 或函数策略。
- 编码、注释、大小写、Unicode 混淆和多语句载荷均以解析后的 AST 与对象解析结果判定，不依赖正则
  或自然语言关键词作为最终防线。
