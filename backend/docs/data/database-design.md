# 数据库设计 v1.0

## Schema 划分

- `mart`：供 Text2SQL 只读查询的经营数据。
- `app`：会话、配置、反馈和审计，由应用读写，禁止 Text2SQL 访问。

## 业务模型

```text
business_units ─┬─ sales_targets
                ├─ contracts ─┬─ revenue_facts
industries ─────┤             └─ payment_facts
product_lines ──┤
customers ──────┘
contracts ─────── project_pipeline
```

## 设计规则

- 主键 UUID；维表另有稳定业务编码。
- 金额统一元，禁止浮点类型。
- 月度/季度/年度均从日期事实聚合，不保存 12 月宽列。
- 删除平台数据优先软删除；业务 Seed 数据不提供在线修改。
- 所有表包含 `created_at`，可变表包含 `updated_at`。
- 常用过滤组合建立索引：年度+经营单元、确认日期、产品线、行业、风险等级。
- `app.idempotency_records` 保存全局幂等键与 operation、resource、SHA-256 请求指纹及
  原 session/message/execution 标识。幂等占位与对应业务对象同事务写入。
- 执行状态转换使用 `UPDATE ... WHERE status IN (...)`。终态不依赖 ORM 旧快照直接覆盖。
- `qa_executions` 保存 `lease_owner/lease_expires_at/heartbeat_at/run_attempt`，支持多实例原子领取、
  心跳续租和过期接管；终态或等待输入时清空租约。
- `qa_execution_effects` 保存稳定 effect key、逻辑尝试、状态和脱敏输出，唯一约束防止
  checkpoint 重放重复写入平台副作。
- `qa_execution_steps.effect_key` 在单次 execution 内唯一，保证步骤审计幂等。
- `qa_execution_events` 保存 append-only SSE 历史；`(execution_id, sequence)` 和
  `(execution_id, dedupe_key)` 均唯一。事件与对应业务事务一起提交，连接本身不生成历史。
- `qa_executions.event_sequence_floor` 记录已清理事件的最大 sequence，用于把过旧重连游标稳定映射为
  HTTP 410。清理只针对已进入终态且超过保留期的 execution，并先推进 floor 再删除事件。
- `qa_executions.context_provenance` 保存解析后的上下文来源、消息/文档标识、选择方式与脱敏错误类别；
  不保存 system prompt、模型思维链、密钥或数据库原始异常。

## 账号

- `app_rw`：仅应用 Schema 读写及业务 Schema 只读。
- `text2sql_ro`：仅 `mart` 白名单视图 SELECT，无 `app` 权限。
- `migration_owner`：只用于迁移，不用于服务运行。

## 数据视图

为降低 Text2SQL 难度，提供语义视图：

- `mart.v_sales_performance`：合同、收入、回款、组织、行业、产品的扁平分析视图。
- `mart.v_target_achievement`：年度目标与收入完成率。
- `mart.v_pipeline_risk`：项目阶段和风险。

模型优先查询视图；基础表仅在复杂问题时开放。
