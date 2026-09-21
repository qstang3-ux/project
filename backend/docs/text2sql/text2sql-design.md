# Text2SQL 设计 v1.0

## 流程

`LangGraph 上下文装载 → 工作记忆 → 独立意图分类/槽位检查 → 条件路由 →（仅 data_query）pgvector/关键词混合 RAG → 真实模型结构化 SQL 生成 → AST校验/改写 → 只读执行 → 一次受控模型纠错 → 真实模型结果总结/图表/追问 → 程序化核验 → checkpoint/业务持久化`

## 意图与槽位

- 意图枚举固定为 `data_query`、`clarification`、`business_definition`、`product_help`、
  `chat`、`out_of_scope`、`unsafe`。
- 分类器只能返回 `intent`、`normalizedQuestion`、`missingSlots`、`confidence`、
  `reasonCode`；这些字段用于路由和审计，不保存模型思维链。
- 只有 `data_query` 可以进入知识召回、SQL 生成、AST 校验和只读执行节点。
- `chat`、`business_definition` 和 `product_help` 不进入 SQL 链路，但在真实模型模式下仍由
  受控结构化 Prompt 生成直接答案；简单算术归入 `chat`。回答不得声称查询了经营数据库，
  图表固定为 `none`。`out_of_scope` 使用固定范围提示，`unsafe` 使用固定安全拒绝，二者不再次调用模型。
- 上下文分为两个通道：SQL 通道只接受同会话、已完成的 `data_query` 快照；会话通道可读取
  同一会话最近已完成的普通对话，仅供意图识别和非 SQL 回答。会话通道始终标记为不可信，
  不得进入 RAG、SQL 生成、对象白名单或数据库错误纠错。
- `unsafe` 可以在分类后提前拒绝；凡是进入 SQL 路径的候选 SQL 仍必须通过 AST Validator，
  分类结果不能旁路最终安全防线。
- 信息不足时持久化结构化澄清请求，执行状态为 `awaiting_input`。用户补充通过同一 execution、
  graph thread 和 checkpoint 恢复；补充内容保存为关联该 execution 的用户消息。
- 单次 execution 最多发起 2 轮澄清；SQL 自动纠错仍最多 1 次。

## Schema 上下文

- 优先暴露三个语义视图及字段说明、Join、指标公式、数据截止日。
- pgvector 语义召回与关键词召回融合，默认知识 Top 5，再归并为最多 6 个允许对象。
- Prompt 带 6～10 条高质量 Few-shot，不包含密钥和连接信息。

知识库仅索引审核后的 Schema、字段、指标、Join、口径和 Few-shot，不索引 API Key、连接串、平台配置或完整业务事实行。

## 结构化输出

意图分类与 SQL 生成使用两个独立的结构化输出。分类输出见上节；SQL 生成输出仅包含
`assumptions`、`sql`、`selectedObjects`。任一结构解析失败均不执行 SQL。

## 纠错

只有执行器根据 PostgreSQL SQLSTATE 明确分类为可恢复的语法、未定义表/列/函数、
分组、类型或转换错误允许一次纠错。超时、取消、安全拒绝、权限、连接、资源、
锁、系统或未知错误不纠错。纠错模型只接收稳定的脱敏错误类别，不接收数据库原始错误文本。
纠错 SQL 必须重新完整校验。

## 幂等与终态一致性

- 创建查询、提交澄清、编辑重发和重新生成共用全局幂等键命名空。
- 幂等键同时绑定 operation、resource（session/message/execution）和规范化请求体 SHA-256。
  同键同请求返回原 session/message/execution；同键不同请求返回
  `IDEMPOTENCY_KEY_CONFLICT`，不创建任何业务对象。
- 幂等占位与 session/message/execution 在同一短事务中提交，不允许孤儿分支会话、
  消息或执行记录。
- `queued -> running` 以及 `running -> completed/failed/rejected/awaiting_input`、
  `queued|running|awaiting_input -> cancelled` 使用数据库条件更新。终态持久化的消息、
  答案版本和审计步骤与该条件更新同事务提交；取消先成功时，运行线程必须回滚未提交的终态副作用。

## Checkpoint 恢复、效果幂等与租约

- 每个有副作的图节点使用由节点、澄清轮次和逻辑尝试组成的稳定 `effect_key`。
  `app.qa_execution_effects` 对 `(execution_id, effect_key)` 建立唯一约束。
- 已完成的模型输出、SQL 结果和持久化结果保存脱敏 JSON 效果。Checkpoint 重放时直接复用
  completed effect，不重复追加模型审计、SQL 执行审计、消息、答案版本或 step。
- 外部调用前先持久化 started effect。进程在外部调用后、效果提交前中断时，恢复运行可重做
  该只读/幂等外部操作，但平台审计和业务副作仍只提交一次。
- 执行运行前必须原子领取租约。`queued` 可直接领取；`running` 只有在租约过期后才能被其他
  实例接管。活动 owner 定期心跳续租，所有终态写入同时校验 owner。
- 取消不受 owner 限制，但仅能从活动状态 CAS 为 `cancelled` 并清理租约。旧 owner 后续提交
  effect 或终态时必须因租约丢失而回滚。
- 启动恢复和显式恢复命令只扫描有界 batch，仅处理 `queued` 或租约已过期的 `running`；
  不自动运行 `awaiting_input`、`cancelled` 或其他终态。恢复继续使用已持久化的模型预算、
  HTTP attempt 和 checkpoint 中的纠错计数。

## 持久化执行事件与 SSE 重连

- `app.qa_execution_events` 是执行事件的唯一事实源。事件按 execution 分配从 1 开始的单调
  sequence，对外事件 ID 固定为 `<execution UUID>:<sequence>`。
- `execution.started` 与创建 execution 同事务写入；step、`clarification.required` 和终态事件
  与对应业务状态、step/effect、消息及答案版本同事务写入。
- 每个事件使用稳定 `dedupe_key`，并由 `(execution_id, dedupe_key)` 唯一约束保护；checkpoint、
  effect 或 worker 恢复重放不得产生重复事件。每个 execution 只允许一个 started 和一个终态事件。
- SSE 首连读取持久历史；重连仅读取 `Last-Event-ID` 之后的事件。Header 优先于
  `lastEventId` query fallback。跨 execution、格式非法和已被保留策略清理的游标必须显式拒绝。
- SSE 轮询每批有上限，空闲连接只发送无 ID 的 keepalive 注释；keepalive 不写事件表，也不参与重放。
  客户端断开或协程取消时立即关闭轮询使用的短数据库会话。

## 答案约束

- 答案只基于结果 JSON 和指标口径；关键数字程序化交叉检查。
- 空结果明确说明；截断结果声明上限。
- 图表只返回白名单类型和存在字段。
- 保存可审计步骤摘要，不保存思维链。
- 模型只接收必要的列定义、截断标记和受限结果 JSON，不接收数据库密钥、连接串或平台 Schema。
- 后端必须核验回答中的关键数字来自结果集，图表字段真实存在，追问可由当前数据源回答。

## 运行模式

- Fake Adapter 仅用于测试、CI 和显式本地离线开发。
- `demo`、`prod` 必须使用真实模型；未配置时失败关闭，不允许静默降级。

## LangGraph 节点

固定节点为：`load_context`、`build_memory`、`classify_intent`、`retrieve_knowledge`、
`generate_sql`、`validate_sql`、`execute_sql`、`correct_sql`、`summarize_result`、
`verify_answer`、`persist_result`、`persist_clarification`、`persist_non_data_response`。
条件边只允许意图路由、安全拒绝、等待输入、取消、失败、一次纠错和成功终态，不允许模型自由创建节点或无限循环。图调用显式使用 `recursion_limit=30`。

单次运行同时受执行 deadline、逻辑模型调用次数和每次调用 HTTP attempt 预算约束。预算耗尽或 deadline 超时必须失败关闭，
不得继续调用模型、执行 SQL 或回退到 Fake/模板问数结果。

## 多轮

- 最近 6 条消息生成结构化上下文：年份、时间范围、经营单元、行业、产品线、指标。
- 指代无法唯一解析时返回澄清选项，不执行猜测 SQL。
- 编辑历史问题创建新 session 分支；重新生成关联旧 execution。

## Prompt Injection 与上下文隔离

- 模型请求分为可信控制面和不可信数据面。System 消息只包含任务、输出 Schema、安全边界和
  allowlist；当前用户输入、历史消息、RAG 文档、查询结果、候选 SQL 与数据库错误类别均放入带
  `channel/source/trust/provenance` 的结构化数据段。
- 数据段中的“忽略规则”“切换角色”“输出密钥”等文字只作为引用内容，不得覆盖 system/developer
  规则、业务元数据、SQL allowlist、模型预算或输出 Schema。安全不依赖关键词封禁；最终边界仍由
  结构化输出校验、SQL AST Validator、只读账号和终态事务共同保证。
- 历史上下文仅允许同 session、已完成且 intent=`data_query` 的消息。显式 context IDs 必须全部满足
  该约束；未显式提供时只选择当前 execution 创建前的最近可信消息，并把解析后的 message IDs 快照
  持久化到 execution。
- resubmit 新分支默认从空上下文开始，`source_message_id` 只记录来源，不自动喂给模型；regenerate
  复制原 execution 的上下文快照，不读取其后新增消息。clarification 只合并同 execution 的补充记录。
- execution 只保存消息 ID、来源 execution/session、角色、选择方式、RAG document ID/score 和脱敏
  SQLSTATE 类别等 provenance，不保存模型思维链或隐藏 prompt。
- RAG 内容与数据库错误都属于引用数据。RAG 不得扩展 allowlisted objects；纠错只接收固定的可恢复
  SQLSTATE 类别，不接收数据库原始错误文本、SQLSTATE 原码、连接信息或服务端异常。
