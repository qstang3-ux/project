# 开发 Backlog

> 2026-09-20 状态说明：核心 P0/P1 功能已实现并通过现有测试；`ENG-01A` 的根 Git 基线、
> `ENG-01E` 的 GitHub Actions CI 和 `OPS-01` 的生产安全编排已补齐。生产发布仍需在干净 Linux
> 主机执行一次完整验收，不能以 Windows Docker Desktop 验收替代。

| ID | 优先级 | 工作包 | 依赖 | 估算人日 |
|---|---|---|---|---:|
| ENG-01A | P0 | Git、忽略规则、EditorConfig、根命令 | 无 | 0.25 |
| ENG-01B | P0 | React + TypeScript + Vite 骨架 | ENG-01A | 0.25 |
| ENG-01C | P0 | FastAPI + Ruff + MyPy + Pytest 骨架 | ENG-01A | 0.25 |
| ENG-01D | P0 | PostgreSQL Compose 开发环境 | ENG-01A | 0.25 |
| ENG-01E | P0 | 统一质量命令和 CI | ENG-01B,ENG-01C | 0.25 |
| ENG-01F | P0 | OpenAPI 校验与 TS 类型生成 | ENG-01B,ENG-01C | 0.25 |
| DB-01 | P0 | SQLAlchemy 模型、Alembic、双 Schema | ENG-01 | 2 |
| DB-02 | P0 | 固定 Seed、语义视图、断言 | DB-01 | 2 |
| API-01 | P0 | FastAPI 基础、错误、分页、健康检查 | ENG-01 | 1.5 |
| CFG-01 | P0 | 模型/应用配置 API | DB-01,API-01 | 2 |
| QA-01 | P0 | 会话、消息、收藏 CRUD | DB-01,API-01 | 2 |
| LG-01 | P0 | LangGraph Typed State、节点、条件路由和图版本 | API-01 | 1.5 |
| LG-02 | P0 | PostgreSQL Checkpointer、恢复、取消和幂等 | LG-01,DB-01 | 1.5 |
| RAG-01 | P0 | pgvector 安装、Alembic 扩展和向量表 | DB-01 | 1.5 |
| RAG-02 | P0 | BGE 中文 Embedding、知识切片和幂等入库 | RAG-01 | 1.5 |
| RAG-03 | P0 | 向量+关键词混合召回、元数据过滤和评测 | RAG-02,DB-02 | 2 |
| T2S-01 | P0 | LangGraph RAG 节点、上下文管理和 Prompt | LG-01,RAG-03 | 2 |
| T2S-02A | P0 | OpenAI-compatible 真实模型 Adapter、结构化输出、重试与审计 | CFG-01 | 1.5 |
| T2S-02B | P0 | LangGraph Agent 编排：SQL 生成、一次纠错、结果总结、图表与追问 | LG-01,T2S-02A,T2S-03 | 2 |
| T2S-02C | P0 | 真实模型冒烟脚本、8 问题评测和脱敏证据 | T2S-02B,DB-02 | 1 |
| T2S-FAKE | P0 | 仅供测试/CI/显式本地离线模式的 Fake Adapter | DB-02,API-01 | 1 |
| T2S-03 | P0 | AST 校验、改写、只读执行 | DB-02 | 2.5 |
| T2S-04 | P0 | Agent 输出校验、关键数字核验和图表字段校验 | T2S-01..03 | 2 |
| T2S-05 | P0 | SSE、取消、执行审计 | T2S-04 | 2 |
| FE-01 | P0 | Shell、路由、API Client、主题 | ENG-01 | 2 |
| FE-02 | P0 | 会话、输入、数据源、快捷问题 | FE-01,QA-01 | 3 |
| FE-03 | P0 | 消息、步骤、SQL、表格、图表 | FE-01,T2S-05 | 3 |
| FE-04 | P0 | 编辑重发、版本、错误状态 | FE-03 | 2 |
| FE-05 | P0 | 模型与应用配置 | FE-01,CFG-01 | 2 |
| FB-01 | P0 | 反馈/校对/日志前后端 | QA-01,FE-01 | 3 |
| TEST-01 | P0 | 单元、集成、E2E、安全评测 | 全部 | 4 |
| OPS-01 | P0 | Docker、Nginx、Linux冒烟、文档 | ENG-01 | 2 |
| EXP-01 | P1 | CSV/PNG 导出 | FE-03 | 1.5 |

执行顺序严格按依赖；单任务超过 2 人日时在 Issue 中继续拆分。
