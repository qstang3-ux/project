# 决策与假设记录

| ID | 决策 | 原因 | 后续可变更点 |
|---|---|---|---|
| ADR-001 | Monorepo：`frontend/`、`backend/`、`data/`、`docs/` | 便于联调、Review、部署 | 团队扩大可拆仓 |
| ADR-002 | React + TypeScript + Vite + Ant Design + ECharts | 组件生态成熟，适合数据应用 | UI 库可替换 |
| ADR-003 | FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL | Python 约束、类型和文档友好 | 无 |
| ADR-004 | 平台表使用 `app` Schema，业务表使用 `mart` Schema | 隔离平台写入与问数只读数据 | 可拆数据库 |
| ADR-005 | Text2SQL 仅允许 `mart` 白名单只读查询 | 最小权限 | 无 |
| ADR-006 | SSE 返回可审计步骤，不输出模型思维链 | 可解释且避免泄露内部推理 | 无 |
| ADR-007 | 验收数据使用固定 Seed，金额单位统一为“元”，接口附带展示单位 | 避免随机结果和精度问题 | 无 |
| ADR-008 | 月度收入/回款采用事实表行，不采用 Excel 12 月宽列 | 便于时间查询和聚合 | 导入时做字段转换 |
| ADR-009 | 编辑历史问题创建分支，重新生成创建回答版本 | 保留审计，不覆盖历史 | MVP UI 可只展示最新版本 |
| ADR-010 | 首个模型适配 OpenAI-compatible Chat API | 兼容多家供应商 | 后续增加原生适配器 |
| ADR-011 | 不实现登录，身份由后端配置注入 | 遵循当前产品范围 | 将来接入 SSO |
| ADR-012 | 先交付零调用费的浏览器 Web Speech STT/TTS；云端、自托管和实时语音对话延期 | 用户选择免费方案，且浏览器能力不改变既有 Agent 安全链路 | 浏览器兼容性不足时升级为后端 Speech Provider |
| ADR-013 | Fake Adapter 仅用于测试、CI 和显式本地离线开发；受控运行环境必须配置真实模型且失败关闭 | 防止固定规则冒充 Text2SQL | 可增加备用真实模型，但不得自动回退 Fake |
| ADR-014 | 真实模型经 OpenAI-compatible 协议接入 | 隔离供应商差异并保持可替换性 | 保留协议字段，可显式切换其他真实模型 |
| ADR-015 | Agent 编排使用 LangGraph `StateGraph`，现有 Retriever、Validator、Executor 和 Adapter 作为节点服务复用 | 显式表达状态、条件分支、一次纠错、恢复和流式进度，不推翻已有安全边界 | 不引入无限 ReAct 或任意工具调用 |
| ADR-016 | 向量数据库使用 PostgreSQL `pgvector`，知识表放在 `app` Schema | 复用 PostgreSQL、事务和备份体系，避免再维护独立数据库 | Windows 扩展安装失败时再记录替代决策，不同时维护两套实现 |
| ADR-017 | 默认中文 Embedding 使用 `BAAI/bge-small-zh-v1.5`，512 维、CPU 本地推理 | 业务知识以中文为主，本地小模型外部依赖少 | Embedding Provider 保持接口化，可替换远程服务 |
| ADR-018 | 开发/演示与生产使用独立 Compose；生产密码使用 Docker Secret 文件，Caddy 负责 HTTPS | 避免固定密码、数据库端口暴露和明文密钥进入编排文件 | 可替换为云 Secret Manager、Ingress 或企业网关 |

默认假设：币种为人民币；自然年；时区 `Asia/Shanghai`；收入以确认日期归属月份；取消订单不计入有效合同额。
