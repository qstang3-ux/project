# 模型接入规格

- 首版协议：OpenAI-compatible `/chat/completions`；适配器接口隔离具体 SDK。
- 默认温度：SQL 生成和答案总结均为 0，降低结构化输出与数字复述的随机性。
- 超时：连接 5s、总请求 60s；网络/429/5xx 最多重试 2 次，指数退避。
- 记录模型名、耗时、输入/输出 Token、状态，不记录密钥。
- 密钥优先环境 Secret；数据库持久化时使用 `MODEL_SECRET_KEY` 的 AEAD 加密。
- API 仅返回 `hasApiKey` 和尾四位掩码。
- 连接测试使用最小无敏感业务数据请求。
- 受控运行环境配置主模型和备用模型；切换需显式，不自动用不同模型产生不可追溯答案。
- 单元测试使用 Fake Adapter，CI 不调用付费模型。

## 环境策略

- `test`、CI：允许 Fake Adapter，确保工程链路确定性。
- `local`：只有显式开启离线模式时允许 Fake；默认建议连接真实模型。
- `demo`、`prod`：必须配置并启用真实模型；缺失配置时返回 `MODEL_NOT_CONFIGURED`，禁止自动回退 Fake。
- 真实模型至少承担结构化 SQL 生成、基于受限结果 JSON 的答案/图表/追问生成，以及
  `chat`、`business_definition`、`product_help` 三类非 SQL 请求的受控直接回答。
- 非 SQL 直接回答仍使用 JSON 结构化输出和不可信数据隔离；不得访问数据库或工具，图表固定为
  `none`。`out_of_scope` 与 `unsafe` 保持确定性范围提示或安全拒绝，不追加模型调用。
- 所有模型输出均视为不可信输入：SQL 必须经过 AST 校验；答案关键数字和图表字段必须由程序验证。
- 答案中的数字只能逐字来自问题、查询结果或程序提供的 `rowCount`；单位必须与结果一致，禁止模型自行换算万元/亿元，也禁止生成阈值、差额、合计、均值等派生数字。

## 结构化 Prompt 边界

- System 消息承载不可被覆盖的任务规则、输出 JSON Schema、秘密保护、对象 allowlist 和“数据段内
  指令不可执行”规则。
- User 消息只发送 JSON 数据信封。当前问题、历史消息、召回知识、候选 SQL、查询结果和脱敏错误
  类别分别标记 channel、source、trust=`untrusted` 与最小 provenance。
- 普通会话历史与问数历史分通道装载：前者只提供给意图分类和非 SQL 回答，后者才可进入
  Text2SQL 上下文。普通会话内容不能扩展 Schema、对象 allowlist 或工具权限。
- 可信 schema 字段说明与 RAG 命中文本必须分开；RAG 文本即使来自内部索引也按不可信引用处理，
  不能新增表、列、函数或改变 SQL 安全策略。
- 模型返回额外字段、未知枚举、未召回对象、非法图表字段或无法解析的 JSON 时立即
  `MODEL_INVALID_RESPONSE`，不得通过追加调用、扩大对象范围、提高预算或切换 Fake 模型来兜底。
- Prompt、历史正文、RAG 正文和数据库原始错误不得写入普通日志或模型调用审计；审计仅保存 purpose、
  provider/model、Token、耗时、状态、稳定错误码和 provenance 标识。

## API 协议

- 模型配置必须明确选择 `responses` 或 `chat_completions`。
- `responses` 调用 `{baseUrl}/responses`，解析 `output_text` 或
  `output[].content[].output_text`，Token 使用 `usage.input_tokens/output_tokens`。
- `chat_completions` 调用 `{baseUrl}/chat/completions`，解析
  `choices[0].message.content`。
- `gpt-5.6-sol` 必须使用 Responses API；创建、更新、连接测试和运行时均会归一到
  `responses`。
- 连接测试不仅检查 HTTP 状态，还必须验证 JSON Content-Type、协议响应结构及最小 JSON 输出。
  HTTP 200 HTML 页面不得视为连接成功。

## 真实冒烟

真实冒烟只能通过运行时环境变量提供密钥：

```powershell
$env:DEFAULT_MODEL_CONFIG="real"
$env:REAL_MODEL_BASE_URL="https://provider.example/v1"
$env:REAL_MODEL_API_KEY="<runtime-secret>"
$env:REAL_MODEL_NAME="gpt-5.6-sol"
$env:REAL_MODEL_PROTOCOL="responses"
python scripts/smoke_real_model.py --output .runtime/real-model-smoke.json
```

如果 API Key 已通过模型配置页面加密保存到数据库，可避免再次把明文密钥放入进程环境：

```powershell
python scripts/smoke_real_model.py --use-active-config --output .runtime/real-model-smoke.json
```

该模式要求存在已启用、已激活且返回密钥掩码的模型配置；报告中的模型名和协议从脱敏配置接口读取。

已有报告可在不产生新供应商调用的情况下按当前验收规则重新校验：

```powershell
python scripts/smoke_real_model.py --revalidate .runtime/real-model-smoke-20260918-final.json
```

报告不会包含 API Key，包含 8 条核心问题、5 条危险请求、执行 ID、模型调用审计、Token、耗时、
SQL 校验状态和结果正确性。缺少任一真实模型环境变量时脚本立即退出，不能使用 Fake 补位。

具体实施与验收见 [真实 Agent 交付计划](real-agent-delivery-plan.md)。
