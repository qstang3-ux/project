# 前端 API 契约问题

记录日期：2026-09-17。前端实现以 `backend/docs/api/openapi.yaml` 为唯一字段事实来源，以下差异未通过前端猜测补齐。

## 待后端确认

1. 执行步骤数量不一致：前端需求要求展示“分析问题”和最终“已完成”在内的 7 个阶段；`ExecutionStepType` 仅定义 5 个阶段。当前前端展示契约中的 5 个可审计步骤，并用执行状态表达完成。
2. 消息与执行记录关联存在历史数据不一致：较早记录中 AI 消息可能出现 `executionId: null`；安全拒绝或取消执行可能只有用户消息携带执行 ID、没有 AI 消息。前端现同时使用用户和 AI 消息的执行关联恢复详情并按执行 ID 去重，但完全缺少执行 ID 的历史记录仍只能降级展示文本。
3. 图表字段未声明必须属于结果列，且 `ChartSpec` 对不同图表类型没有判别联合约束。前端会校验必要字段，异常时降级保留表格。
4. `ResultColumn` 没有提供展示控制或字段角色，例如 `visible`、`semanticType`、`isIdentifier`。前端当前仅按字段 key/label 隐藏明显的 ID、UUID、GUID、主键和行号列；建议后端补充结构化展示元数据，避免依赖命名约定。

## 已由契约更新解决

- `ExecutionDetail.sqlValidationStatus` 已提供结构化 SQL 校验状态，前端已按 `not_started`、`passed`、`rejected` 展示。
- 2026-09-16 真实执行详情抽样已稳定返回 `sqlValidationStatus`；前端仍保留步骤状态降级逻辑以兼容旧记录。
- 反馈和问答日志已补充 `userId`。
- SSE 事件已增加按事件类型区分的数据 schema。
- `ExecutionDetail.result`、`chart`、`error` 已明确为 required nullable 字段。
- `QaLogDetail` 已补充并在真实接口返回 `graphVersion`、`graphNodeTrace`、`checkpointStatus`、`ragDocumentIds`、`ragDegraded` 和 `modelCalls`。
- 澄清契约已补齐：`awaiting_input`、`intent`、`normalizedQuestion`、`missingSlots`、`clarificationRound`、`clarification`、`POST /qa/executions/{executionId}/clarifications` 与 `clarification.required` 事件均已由前端直接消费。
- 2026-09-16 真实 HTTP 验证已确认澄清提交继续原 execution，不创建新 execution；补充消息与原问题共用同一 execution ID。
- 反馈说明、推荐问题、模型配置名称和模型名称的长度已在 OpenAPI 收紧为 500/100/50/100，与前端需求一致。
- SSE 已补齐 `execution.completed`、`Last-Event-ID` Header、`lastEventId` query fallback，以及 409/410/422 游标错误。前端已接入事件去重、最多三次有界重连、410 清游标恢复和轮询降级。
- 2026-09-17 真实 HTTP 验证已确认 SSE 游标重放：首连事件 ID 为 `:1` 到 `:7`，使用 `:1` 重连只返回 `:2` 到 `:7`，游标事件不重复。
- `ExecutionDetail.tokenUsage` 已加入 OpenAPI 必填字段，回答卡已展示总 Token，并可查看输入/输出拆分。
- 执行步骤耗时已改为后端真实测量；无法从历史数据恢复时返回 `null`，前端不再显示误导性的 `0ms`。

## 不阻塞项

- 会话列表只提供通用分页，不提供服务端显式排序参数；前端按返回数据展示，契约 Mock 使用“置顶优先、更新时间倒序”。
- 数据源分组固定为 `ledger` / `report`，与当前产品的“台账数据/统计报表”一致；若未来需要自定义分组，应扩展枚举和展示名称字段。
- Agent、RAG 和模型调用审计字段只属于问答日志详情；`/qa/logs` 页面已按 OpenAPI 直接消费，其他页面不重复展示。
- 当前真实环境已启用 DeepSeek `deepseek-flash`（`chat_completions`），连接测试和一条 21 行真实问数全链路已通过；完整 8 条核心问题与 5 条危险请求仍需单独验收。
- 前端 SSE 主链路、免费浏览器语音增强、响应式宽度、快捷提问/收藏、问答日志、编辑分支、重新生成、回答版本和 CSV 导出均已完成，Vitest 25 个文件 47 项和 Playwright 10/10 通过；生产构建仍有约 500 KB 以上的大 chunk 警告。
- 回答版本接口的后端实现已按 `regeneratedFromExecutionId` 聚合完整链路；从原消息或再生成消息查询都会返回相同版本序列，最新完成版本标记为当前。
