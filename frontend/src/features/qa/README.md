# 智能问数模块

问数功能按业务职责组织，不按 React 文件类型平铺：

- `workspace/`：页面级编排、会话与执行状态协调、滚动控制。
- `sessions/`：会话列表及会话管理交互。
- `composer/`：问题输入与数据源选择。
- `conversation/`：消息流、欢迎态和基础消息气泡。
- `answer/`：执行详情、SQL、表格、图表、回答操作与反馈。

模块外部只从 `index.ts` 使用 `QuestionWorkspace`。子目录之间通过明确的业务组件协作，API 请求仍统一经过 `src/api/`。
