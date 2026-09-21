# 前端设计 v1.0

## 路由与组件

```text
AppShell
├─ /qa QuestionPage(SessionSidebar, MessageList, Composer, QuickQuestions, SourcePicker)
├─ /settings/application ApplicationSettingsPage
│  └─ ModelSettingsModal（模型配置卡片齿轮打开）
└─ /feedback FeedbackPage + FeedbackDrawer
```

AI 消息拆为 `ExecutionSteps`、`SqlViewer`、`ResultTable`、`ResultChart`、`AnswerActions`、`FollowUps`。通用组件包含 ConfirmDialog、AsyncButton、EmptyState、ErrorState、CopyButton。

## 状态

- 服务端状态全部使用 TanStack Query；非敏感 UI 偏好才使用 localStorage。
- SSE 状态机：idle → queued → running → completed/failed/cancelled/rejected。
- SSE 断线最多自动重连 3 次；随后轮询执行详情取得最终状态。
- 查询键以资源 ID 为中心；mutation 成功后精确失效缓存。

## 安全与降级

- 文本默认 React 转义；Markdown 使用白名单渲染器。
- 后端图表描述转换为本地图表配置，不执行服务端 JavaScript。
- 图表失败降级为表格；剪贴板失败提示；无模型/数据源时禁用发送。
- 金额、日期、百分比使用统一 formatter。

## API 类型

以 [后端 OpenAPI 契约](../../backend/docs/api/openapi.yaml) 生成 TypeScript 类型；手写类型不得与契约重复。
