# 前端代码规则

本文件适用于 `frontend/`。同时遵循仓库根目录 `AGENTS.md`。

开始任何前端任务前，必须完整阅读：

1. `frontend/README.md`
2. `frontend/docs/HANDOFF.md`
3. `frontend/docs/requirements.md`
4. `frontend/docs/design.md`
5. `frontend/docs/ui-design-system.md`
6. `docs/00-shared/product-scope.md`
7. `docs/00-shared/acceptance-criteria.md`
8. `docs/00-shared/architecture.md`
9. `docs/01-project-management/backlog.md`
10. `backend/docs/api/openapi.yaml`
11. `backend/docs/api/error-codes.md`

正式行为以前端需求和 OpenAPI 为准；历史原型与演示信息不进入开发必读材料。

## 1. 技术基线

- React + TypeScript + Vite。
- React Router 管理路由。
- TanStack Query 管理服务端状态。
- Ant Design 提供基础组件。
- ECharts 提供图表。
- API 类型从 `backend/docs/api/openapi.yaml` 生成。

## 2. 目录职责

```text
src/
├── api/          生成类型、API Client、请求适配
├── components/   无业务或跨业务公共组件
├── features/     按业务领域组织的组件、Hooks 和类型
├── layouts/      页面框架
├── pages/        路由入口，只做页面组合
├── hooks/        真正跨业务的 Hooks
├── types/        非 OpenAPI 的共享类型
└── utils/        无副作用工具
```

- 禁止把所有问数逻辑堆在一个页面组件中。
- 页面组件不直接拼接 URL 或调用原生 `fetch`，统一通过 `api/`。
- 一个业务功能优先放在同一 `features/<feature>/` 内，避免按文件类型过度分散。
- 所有前端实现、测试和构建配置必须留在 `frontend/`；不得在仓库根目录或 `backend/` 新增前端业务文件。
- 不得修改后端业务实现。若契约缺失或冲突，记录问题并提出所需字段，由后端更新 OpenAPI。

## 3. TypeScript 与 React

- 启用严格 TypeScript。
- 禁止无理由使用 `any`、非空断言和类型强转。
- Props、API 响应和组件状态必须有明确类型。
- 不在 render 中执行网络请求或产生副作用。
- `useEffect` 只用于与外部系统同步，不用于派生普通状态。
- 服务端状态放 TanStack Query；仅短生命周期 UI 状态放组件或本地 Store。
- 列表必须使用稳定业务 ID 作为 key。
- 避免超大组件；出现多个独立状态区或超过约 250 行时优先拆分。

## 4. API 与状态

- OpenAPI 生成类型是接口字段事实来源，不手写重复响应类型。
- Query Key 集中定义，mutation 后精确失效缓存。
- 请求必须处理 loading、empty、error、success 四种状态。
- SSE/轮询状态通过明确状态机管理，不使用零散布尔值组合。
- 不把 API Key、完整 SQL 结果或敏感日志写入 localStorage。

## 5. 安全与展示

- React 默认文本转义，不使用未经清洗的 `dangerouslySetInnerHTML`。
- Markdown 仅允许安全白名单标签。
- 后端图表描述只能转换为本地 ECharts 配置，禁止执行服务端脚本。
- SQL 使用只读展示组件，不允许前端编辑并提交执行。
- API 错误不得展示后端堆栈、连接信息或密钥。

## 6. UI 与可用性

- 使用设计 Token，不在各组件重复散落颜色和尺寸。
- 所有表单元素有 label、校验和提交状态。
- 破坏性操作二次确认。
- 弹窗支持明确取消；存在未保存内容时阻止误关闭。
- 图表失败时降级为表格。
- 键盘焦点可见，核心操作支持键盘。
- 不保留没有行为的按钮；未实现功能必须隐藏或明确禁用。

## 7. 测试与命令

项目应提供并保持以下命令可用：

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm e2e
```

优先测试：

- 问数状态机。
- 会话切换和消息恢复。
- SQL、表格和图表降级。
- 模型和应用配置表单。
- 反馈提交。
- XSS 文本输入。

## 8. 空闲时自主巡检

当前端主任务处于空闲且没有等待用户决策的阻塞时，不得仅保持 idle。应从下列队列中选择一个 30～60 分钟的有界任务，自主检查、复现、修复和验证：

1. 真实接口模式下逐页检查 loading、empty、error、success 和刷新恢复状态。
2. 检查会话切换、消息去重、自动滚动、输入框、弹窗、表单校验和重复提交。
3. 检查 1024×720、1280×720、1440×900 的布局、遮挡、双滚动和图表尺寸。
4. 检查键盘操作、焦点、Enter/Shift+Enter、Esc、Tab 顺序和按钮禁用状态。
5. 对照需求文档和 OpenAPI 检查遗漏，不得复制历史原型的随机数据或固定逻辑。
6. 检查后端 OpenAPI 是否变化；变化时重新生成类型并修复编译问题。
7. 检查真实后端返回的历史消息、执行状态、错误码、nullable 字段和未知文本是否安全降级。
8. 检查 bundle 体积、重复请求、无意义重渲染和明显的控制台错误；只做低风险、有证据的优化。

自主修复规则：

- 只修复可以复现或由测试证明的问题，不进行无需求依据的视觉重做。
- 不修改 `backend/`，契约问题记录到 `frontend/docs/api-issues.md` 并通知协调任务。
- 每次只处理一个明确问题或一组紧密相关问题，增加与风险相称的测试。
- 修改后至少运行受影响的 lint、typecheck 和测试；涉及构建、路由或配置时运行生产构建，涉及核心交互时运行 E2E。
- 最终必须非空报告：发现的问题、修改文件、验证结果、风险和下一巡检候选项。
