# 经管之星后端任务

本目录是独立后端开发对话的工作入口。后端负责数据库、会话、模型配置、Text2SQL、安全执行、日志、反馈和 OpenAPI 契约。

## 新对话开始方式

在新的后端对话中使用：

```text
请实现经管之星后端。工作目录为 backend/。
开始前先阅读根目录 AGENTS.md，再完整阅读 backend/AGENTS.md 中列出的全部必读文档。
先检查当前项目状态，再按照开发 Backlog 的优先级持续实现、测试和验证，
直到后端完成门禁满足或出现必须由我决策的阻塞。
所有后端代码、测试、迁移、Seed、评测、配置和后端文档都放在 backend/，不要修改前端业务实现。
OpenAPI 由后端维护，是前后端接口唯一事实来源；实现前补齐所需 Schema，任何契约变化必须同步文档并在最终报告中单列。
最终报告已完成功能、修改文件、迁移与 Seed、接口与契约变化、验证命令与结果、风险和遗留项。
```

## 必读顺序

1. [后端开发规则](AGENTS.md)
2. [后端交接说明](docs/HANDOFF.md)
3. [后端文档索引](docs/README.md)
4. [共享产品范围](../docs/00-shared/product-scope.md)
5. [共享验收标准](../docs/00-shared/acceptance-criteria.md)
6. [开发 Backlog](../docs/01-project-management/backlog.md)

`backend/AGENTS.md` 中的完整必读清单具有强制性，上述列表只是入口导航。

## 所有权

- 后端拥有 `backend/docs/api/openapi.yaml`。
- 数据库 DDL、迁移、Seed 和评测集全部位于 `backend/`。
- 前端不得直接依赖数据库结构，只依赖 OpenAPI。
- 除仓库级编排确有需要外，不在 `backend/` 之外创建或移动后端文件。

## 开发优先顺序

1. FastAPI、PostgreSQL、迁移和 Seed。
2. 会话、消息、数据源最小 API。
3. Fake Adapter、SQL Validator 和只读执行器。
4. 真实模型 Adapter、答案与图表建议。
5. 模型/应用配置和反馈校对。
6. 安全测试、Docker 和核心评测集回归。

## 本地运行

要求 Python 3.12 和 PostgreSQL 16。所有命令均在 `backend/` 执行。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
alembic upgrade head
python -m app.seed --seed 20260915
python -m app.seed --verify
python scripts/build_rag_index.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

异常中断后可显式执行一次有界恢复：

```powershell
python -m app.recovery --limit 20
```

恢复命令和启动扫描都只处理 queued 或过期 running，不会重跑等待澄清、已取消或终态执行。

SSE 事件默认保留 7 天。本地环境不启动定时清理；运维可显式执行有界清理：

```powershell
python -m app.event_retention --days 7 --limit 100
```

清理只处理超过保留期的终态 execution，并在删除事件前推进 `event_sequence_floor`，因此旧
`Last-Event-ID` 会稳定返回 HTTP 410，而不是静默漏事件。

存活检查为 `GET /health/live`，数据库就绪检查为 `GET /health/ready`，API 文档为
`GET /docs`。固定验收数据使用 Seed `20260915`，数据截止日为 `2026-05-31`。

本地 PostgreSQL 必须安装 `pgvector`，并能成功执行 `CREATE EXTENSION vector`。Windows
项目运行库使用 PostgreSQL 16 对应的扩展文件；迁移 `20260916_0006` 会创建 512 维
`app.rag_documents`、LangGraph checkpoint 表和执行图审计字段。知识索引使用
`BAAI/bge-small-zh-v1.5`，首次构建会下载模型，后续按内容哈希跳过未变化文档。
迁移 `20260916_0012` 为 execution 增加 `context_provenance`，记录消息、RAG 和脱敏错误类别的
来源标识；不保存隐藏 Prompt、数据库原始错误、模型思维链或密钥。

## 数据库账号

- 迁移和 Seed 使用 `migration_owner`。
- 应用平台数据连接使用 `app_rw`。
- Text2SQL 查询必须使用 `text2sql_ro`，该账号只被授予三个 `mart` 语义视图的查询权限。

本地 `.env` 中分别通过 `MIGRATION_DATABASE_URL`、`DATABASE_URL` 和
`QUERY_DATABASE_URL` 配置上述三个账号。Alembic 和 Seed 优先读取迁移连接，API 运行时不会
用迁移所有者连接处理业务请求。

迁移会在对应角色已存在时自动授权。独立环境也可在迁移后执行
`scripts/grant_roles.sql`。不要让服务运行账号使用迁移所有者连接。

## Docker Compose

后端目录提供独立的 pgvector PostgreSQL、迁移、Seed、RAG 索引和 API 编排：

```powershell
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health/ready
```

迁移和 Seed 是显式一次性服务；API 容器不会在启动时重置数据。Seed 重复执行会检查
`app.seed_versions` 并保持幂等。`rag-index` 在 Seed 后执行，只有索引成功才启动 API。

## 验证

```powershell
ruff check .
ruff format --check .
mypy app
pytest
alembic upgrade head
python scripts/evaluate_rag.py --output .runtime/rag-evaluation.json
python scripts/evaluate_prompt_security.py --output .runtime/prompt-injection-report.json
```

Prompt Injection 评测不调用模型，覆盖当前输入、历史、RAG、数据库错误和查询结果五个不可信通道，
并同时回归 `tests/evaluation/text2sql-cases.json` 的 30 条确定性用例。system 消息只保存可信任务配置、
输出 Schema 和对象 allowlist；user 消息只发送结构化 `untrustedData`。

有独立 PostgreSQL 测试库时，先对空库执行迁移和 Seed，再设置
`TEST_DATABASE_URL` 运行集成测试。测试库必须是可丢弃环境。

```powershell
$env:DATABASE_URL=$env:TEST_DATABASE_URL
alembic upgrade head
python -m app.seed --seed 20260915
pytest -m integration
```

## 前端联调

本地前端默认可从 `http://localhost:5173` 或 `http://127.0.0.1:5173` 访问后端。
其他来源通过环境变量 `CORS_ORIGINS` 配置为 JSON 数组；生产环境不要使用通配符来源。

```powershell
$env:DATABASE_URL="postgresql+psycopg://app_rw:app_rw@127.0.0.1:5432/management_star"
$env:QUERY_DATABASE_URL="postgresql+psycopg://text2sql_ro:text2sql_ro@127.0.0.1:5432/management_star"
$env:DEFAULT_MODEL_CONFIG="fake"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- REST 与 SSE 基地址均为 `http://127.0.0.1:8000/api/v1`。
- 提交问题、重发和重新生成必须发送 `Idempotency-Key`，长度为 8～128。
- SSE 使用响应中的 `eventUrl`；断线重连可发送 `Last-Event-ID`。
- `X-Request-ID` 会原样回传；未提供时由后端生成。
- `DEFAULT_MODEL_CONFIG=fake` 仅允许 `local`/`test` 显式离线开发和 CI；Fake 使用固定候选 SQL
  以保证测试确定性，不能计入真实 Agent 验收。`demo`/`prod` 配置 Fake 会启动失败。
- `DEFAULT_MODEL_CONFIG=real` 优先使用已激活的加密模型配置；没有数据库配置时，仅在
  `REAL_MODEL_BASE_URL`、`REAL_MODEL_API_KEY`、`REAL_MODEL_NAME` 全部存在时使用运行时 Secret。
- 模型配置必须声明 `protocol=responses|chat_completions`；`gpt-5.6-sol` 固定使用 Responses API。
- 保存真实模型 API Key 前必须设置非空 `MODEL_SECRET_KEY`。密钥仅加密存储，接口只返回掩码。
- 未启动 PostgreSQL 时 `/health/live` 仍返回 200，`/health/ready` 返回 503；会话、配置和问数
  接口均不可用于联调。先完成迁移和 Seed，再启动前端。
- OpenAPI 唯一契约为 `docs/api/openapi.yaml`；当前 27 个路径的参数、请求体和成功响应字段
  均有自动一致性测试。
- `ExecutionStatus=awaiting_input` 表示正常等待用户补充，不是失败。执行详情中的
  `clarification` 提供提示、缺失槽位和当前/最大轮次；前端提交补充时调用
  `POST /qa/executions/{executionId}/clarifications`，携带新的 `Idempotency-Key` 和
  `{ "content": "..." }`。服务继续同一 execution、SSE 地址、graph thread 与 checkpoint。
- SSE 事件 ID 为 `<execution UUID>:<sequence>`。浏览器自动重连使用 `Last-Event-ID`；手工重连可用
  `lastEventId` query 参数，Header 存在时优先。连接只重放游标之后的持久事件。
- SSE 收到 `clarification.required` 后应结束本次流读取并展示补充输入框；补充接口返回 202 后
  重新订阅原 `eventUrl`。重复提交同一幂等键不会新增消息、事件或重复恢复。
- 显式 Text2SQL 上下文消息只允许来自同一 session 且关联已完成 `data_query`；非法上下文返回
  `CONTEXT_NOT_ALLOWED`。普通会话另取同一 session 最近已完成消息，仅供意图分类和非 SQL 回答，
  并以 `sqlEligible=false` 审计，不能进入 RAG、SQL 生成或对象白名单。编辑重发默认不继承原消息正文，
  重新生成固定使用原 execution 的 Text2SQL 上下文快照，澄清补充只进入同一 execution。

## 真实模型冒烟

真实供应商验证不属于普通 Pytest 门禁。显式设置运行时变量后执行：

```powershell
$env:DEFAULT_MODEL_CONFIG="real"
$env:REAL_MODEL_BASE_URL="https://provider.example/v1"
$env:REAL_MODEL_API_KEY="<runtime-secret>"
$env:REAL_MODEL_NAME="gpt-5.6-sol"
$env:REAL_MODEL_PROTOCOL="responses"
python scripts/smoke_real_model.py --output .runtime/real-model-smoke.json
```

未生成真实报告前，交付状态必须写为“真实供应商端到端未实测”，不得引用 Fake/Mock 结果替代。
