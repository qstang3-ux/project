# 错误码

| 错误码 | HTTP | 含义 |
|---|---:|---|
| VALIDATION_ERROR | 422 | 参数错误 |
| RESOURCE_NOT_FOUND | 404 | 资源不存在 |
| VERSION_CONFLICT | 409 | 并发版本冲突 |
| IDEMPOTENCY_KEY_CONFLICT | 409 | 幂等键已绑定到不同操作、资源或请求体 |
| MODEL_NOT_CONFIGURED | 409 | 无启用模型 |
| FAKE_MODEL_FORBIDDEN | 503 | 当前环境禁止使用 Fake 模型 |
| MODEL_AUTH_FAILED | 502 | 模型鉴权失败 |
| MODEL_NOT_FOUND | 502 | 模型或协议接口不存在 |
| MODEL_INVALID_RESPONSE | 502 | 模型返回非 JSON、错误结构或未通过输出核验 |
| MODEL_TIMEOUT | 504 | 模型超时 |
| MODEL_UNAVAILABLE | 502 | 模型不可用 |
| DATA_SOURCE_UNAVAILABLE | 503 | 数据源不可用 |
| SQL_GENERATION_FAILED | 422 | 无法生成查询 |
| CLARIFICATION_LIMIT_REACHED | 409 | 当前执行已达到最多两轮澄清 |
| EXECUTION_NOT_AWAITING_INPUT | 409 | 当前执行不处于等待补充状态 |
| EXECUTION_DEADLINE_EXCEEDED | 504 | 单次 Agent 执行超过配置 deadline |
| MODEL_BUDGET_EXCEEDED | 429 | 单次执行模型调用次数超过配置预算 |
| SQL_VALIDATION_FAILED | 422 | SQL 被安全规则拒绝 |
| UNSAFE_REQUEST | 422 | 请求涉及写操作、敏感配置或越权访问，已在 SQL 前拒绝 |
| QUERY_TIMEOUT | 504 | 查询超时 |
| QUERY_FAILED | 422 | 查询执行失败 |
| RESULT_TOO_LARGE | 413 | 结果过大 |
| EXECUTION_CANCELLED | 409 | 执行已取消 |
| EXECUTION_LEASE_LOST | 409 | 执行租约已被其他实例接管，当前 worker 停止提交副作用 |
| CONTEXT_NOT_ALLOWED | 422 | 上下文消息不属于当前会话、不是可信已完成 data_query 或位于隔离分支 |
| SSE_EVENT_ID_INVALID | 422 | SSE 重连事件 ID 格式非法、sequence 越界或指向不存在的未来事件 |
| SSE_EVENT_EXECUTION_MISMATCH | 409 | SSE 重连事件 ID 属于其他 execution |
| SSE_EVENT_EXPIRED | 410 | SSE 重连事件已超过服务端保留期并被清理 |
| RATE_LIMITED | 429 | 请求过频 |
| INTERNAL_ERROR | 500 | 未分类服务错误 |

响应统一包含 `error.code/message/requestId/details`，生产环境 details 不含堆栈、连接串和密钥。
