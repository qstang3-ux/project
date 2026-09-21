# 经管之星前端任务

本目录是独立前端开发对话的工作入口。前端负责智能问数、模型配置、应用配置、问答日志和回复校对界面。

## 本地运行

```bash
pnpm install
pnpm generate:api
pnpm dev
```

默认启用严格遵循 OpenAPI 的 MSW 契约 Mock。接入真实后端时设置：

```text
VITE_USE_MOCK=false
VITE_API_BASE_URL=/api/v1
```

完整门禁：

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm e2e
```

## 新对话开始方式

在新的前端对话中使用：

```text
请实现经管之星前端。工作目录为 frontend/。
开始前先阅读根目录 AGENTS.md，再完整阅读 frontend/AGENTS.md 中列出的全部必读文档，
先检查当前项目状态，再按照开发 Backlog 的优先级持续实现、测试和验证，
直到前端完成门禁满足或出现必须由我决策的阻塞。
所有前端代码、测试、配置和前端文档都放在 frontend/，不要修改后端业务实现。
严格遵循 backend/docs/api/openapi.yaml；接口契约有缺失或冲突时记录并明确提出，不要自行猜字段。
最终报告已完成功能、修改文件、验证命令与结果、未接通接口、风险和遗留项。
```

## 必读顺序

1. [前端开发规则](AGENTS.md)
2. [前端交接说明](docs/HANDOFF.md)
3. [前端文档索引](docs/README.md)
4. [共享产品范围](../docs/00-shared/product-scope.md)
5. [共享验收标准](../docs/00-shared/acceptance-criteria.md)
6. [后端 OpenAPI](../backend/docs/api/openapi.yaml)

`frontend/AGENTS.md` 中的完整必读清单具有强制性，上述列表只是入口导航。

## 前后端边界

- 前端只通过统一 API Client 访问后端。
- OpenAPI 是接口字段唯一事实来源。
- 前端不保存 API Key，不执行 SQL，不生成固定业务答案。
- 如果后端尚未完成，使用严格遵循 OpenAPI 的 Mock Server，不在组件中写临时假数据。
- 除仓库级编排确有需要外，不在 `frontend/` 之外创建或移动前端文件。

## 开发优先顺序

1. 应用框架、路由、主题和 API Client。
2. 智能问数完整纵向页面。
3. SQL、表格和图表展示。
4. 模型配置、应用配置、反馈校对。
5. 会话管理、快捷问题和日志。
6. 测试、构建和视觉整理。
