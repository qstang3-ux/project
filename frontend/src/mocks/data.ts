import type {
  ApplicationConfig,
  DataSource,
  ExecutionDetail,
  FeedbackDetail,
  Message,
  ModelConfig,
  Session,
} from '../api/types';

const now = new Date('2026-09-16T03:00:00.000Z').toISOString();

export const ids = {
  sourceLedger: '11111111-1111-4111-8111-111111111111',
  sourceReport: '22222222-2222-4222-8222-222222222222',
  session: '33333333-3333-4333-8333-333333333333',
  userMessage: '44444444-4444-4444-8444-444444444444',
  assistantMessage: '55555555-5555-4555-8555-555555555555',
  execution: '66666666-6666-4666-8666-666666666666',
  model: '77777777-7777-4777-8777-777777777777',
  feedback: '88888888-8888-4888-8888-888888888888',
};

export const dataSources: DataSource[] = [
  {
    id: ids.sourceLedger,
    name: '经营目标台账',
    description: '经营单元年度目标与完成情况',
    group: 'ledger',
    enabled: true,
    isDefault: true,
    dataAsOf: '2026-08-31',
    allowedObjects: ['mart.business_targets', 'mart.operating_units'],
  },
  {
    id: ids.sourceReport,
    name: '收入统计报表',
    description: '产品线与月度收入汇总',
    group: 'report',
    enabled: true,
    isDefault: true,
    dataAsOf: '2026-08-31',
    allowedObjects: ['mart.monthly_revenue', 'mart.product_lines'],
  },
];

export let sessions: Session[] = [
  {
    id: ids.session,
    title: '2026 年经营目标分析',
    pinned: true,
    messageCount: 2,
    lastMessagePreview: '商业目标最高的经营单元是哪些？',
    createdAt: now,
    updatedAt: now,
  },
];

export const messagesBySession = new Map<string, Message[]>([
  [
    ids.session,
    [
      {
        id: ids.userMessage,
        sessionId: ids.session,
        role: 'user',
        content: '2026年商业目标最高的5个经营单元',
        executionId: ids.execution,
        executionStatus: 'completed',
        createdAt: now,
      },
      {
        id: ids.assistantMessage,
        sessionId: ids.session,
        role: 'assistant',
        content: '2026年商业目标最高的5个经营单元中，北京代表处位居第一。前五名商业目标合计31,130万元。',
        sourceMessageId: ids.userMessage,
        executionId: ids.execution,
        executionStatus: 'completed',
        currentVersionNo: 1,
        createdAt: now,
      },
    ],
  ],
]);

export const createCompletedExecution = (
  executionId: string,
  sessionId: string,
  userMessageId: string,
  question: string,
  sourceIds: string[],
): ExecutionDetail => ({
  id: executionId,
  requestId: `mock-${executionId.slice(0, 8)}`,
  sessionId,
  userMessageId,
  assistantMessageId: crypto.randomUUID(),
  question,
  intent: 'data_query',
  normalizedQuestion: question,
  missingSlots: [],
  clarificationRound: 0,
  clarification: null,
  dataSourceIds: sourceIds,
  status: 'completed',
  sqlValidationStatus: 'passed',
  steps: [
    { type: 'intent_classification', status: 'completed', summary: '已识别为经营数据查询', durationMs: 42 },
    { type: 'schema_selection', status: 'completed', summary: '已选择经营目标与经营单元数据对象', durationMs: 86 },
    { type: 'sql_generation', status: 'completed', summary: '已生成只读查询', durationMs: 132 },
    { type: 'sql_validation', status: 'completed', summary: 'AST 安全校验通过，仅包含 SELECT', durationMs: 18 },
    { type: 'query_execution', status: 'completed', summary: '查询完成，返回 5 行', durationMs: 74 },
    { type: 'answer_generation', status: 'completed', summary: '已生成结论与推荐追问', durationMs: 205 },
  ],
  selectedObjects: ['mart.business_targets', 'mart.operating_units'],
  sql: 'SELECT operating_unit, analysis_year, commercial_target\nFROM mart.business_targets\nWHERE analysis_year = 2026\nORDER BY commercial_target DESC\nLIMIT 5;',
  result: {
    columns: [
      { key: 'operating_unit', label: '经营单元', dataType: 'string' },
      { key: 'analysis_year', label: '年度', dataType: 'integer' },
      { key: 'commercial_target', label: '商业目标', dataType: 'decimal', unit: '万元' },
    ],
    rows: [
      { operating_unit: '北京代表处', analysis_year: 2026, commercial_target: '7950' },
      { operating_unit: '上海代表处', analysis_year: 2026, commercial_target: '7070' },
      { operating_unit: '浙江代表处', analysis_year: 2026, commercial_target: '6460' },
      { operating_unit: '江苏代表处', analysis_year: 2026, commercial_target: '5560' },
      { operating_unit: '山东代表处', analysis_year: 2026, commercial_target: '4090' },
    ],
    rowCount: 5,
    truncated: false,
  },
  answer: '北京代表处以7,950万元居首，其次是上海、浙江、江苏和山东代表处。前五名商业目标合计31,130万元。',
  chart: { type: 'bar', title: '2026年商业目标 Top 5', xField: 'operating_unit', yFields: ['commercial_target'], unit: '万元' },
  followUpQuestions: ['它们的商解目标呢？', '这些经营单元的目标完成率如何？', '北京代表处1到8月收入趋势'],
  modelName: '经营分析模型',
  tokenUsage: { promptTokens: 968, completionTokens: 214, totalTokens: 1182 },
  currentVersionNo: 1,
  durationMs: 515,
  error: null,
  createdAt: now,
  completedAt: now,
});

export const createAwaitingClarificationExecution = (
  executionId: string,
  sessionId: string,
  userMessageId: string,
  question: string,
  sourceIds: string[],
  round = 1,
): ExecutionDetail => {
  const firstRound = round === 1;
  const missingSlots = firstRound ? ['metric', 'dimension'] : ['time_range'];
  return {
    id: executionId,
    requestId: `mock-${executionId.slice(0, 8)}`,
    sessionId,
    userMessageId,
    assistantMessageId: null,
    question,
    intent: 'clarification',
    normalizedQuestion: firstRound ? '查询经营目标达成情况' : '查询各经营单元商业目标完成率',
    missingSlots,
    clarificationRound: round,
    clarification: {
      prompt: firstRound ? '请补充要查询的指标和分析维度。' : '请再补充查询年份或时间范围。',
      missingSlots,
      round,
      maxRounds: 2,
    },
    dataSourceIds: sourceIds,
    status: 'awaiting_input',
    sqlValidationStatus: 'not_started',
    steps: [
      { type: 'intent_classification', status: 'completed', summary: '已识别问题，但查询条件不完整', durationMs: 38 },
      { type: 'clarification_required', status: 'completed', summary: `等待第 ${String(round)} 轮补充信息`, durationMs: 12 },
    ],
    selectedObjects: [],
    sql: null,
    result: null,
    answer: null,
    chart: null,
    followUpQuestions: [],
    modelName: '经营分析模型',
    tokenUsage: { promptTokens: 188, completionTokens: 42, totalTokens: 230 },
    currentVersionNo: null,
    durationMs: null,
    error: null,
    createdAt: now,
    completedAt: null,
  };
};

export const createClarificationCompletedExecution = (
  execution: ExecutionDetail,
  normalizedQuestion: string,
): ExecutionDetail => {
  const completed = createCompletedExecution(execution.id, execution.sessionId, execution.userMessageId, execution.question, execution.dataSourceIds);
  const rows = Array.from({ length: 21 }, (_, index) => ({
    operating_unit: `经营单元${String(index + 1).padStart(2, '0')}`,
    analysis_year: 2026,
    completion_rate: String(55 + index * 2),
  }));
  return {
    ...completed,
    normalizedQuestion,
    clarificationRound: execution.clarificationRound,
    selectedObjects: ['mart.v_target_achievement'],
    sql: 'SELECT operating_unit, analysis_year, completion_rate\nFROM mart.v_target_achievement\nWHERE analysis_year = 2026\nORDER BY completion_rate ASC;',
    result: {
      columns: [
        { key: 'operating_unit', label: '经营单元', dataType: 'string' },
        { key: 'analysis_year', label: '年度', dataType: 'integer' },
        { key: 'completion_rate', label: '完成率', dataType: 'percent' },
      ],
      rows,
      rowCount: rows.length,
      truncated: false,
    },
    answer: '2026年各经营单元商业目标完成率已按从低到高排列，共返回21个经营单元。',
    chart: { type: 'bar', title: '2026年商业目标完成率', xField: 'operating_unit', yFields: ['completion_rate'], unit: '%' },
  };
};

export const createRejectedExecution = (
  executionId: string,
  sessionId: string,
  userMessageId: string,
  question: string,
  sourceIds: string[],
): ExecutionDetail => ({
  id: executionId,
  requestId: `mock-${executionId.slice(0, 8)}`,
  sessionId,
  userMessageId,
  assistantMessageId: crypto.randomUUID(),
  question,
  intent: 'unsafe',
  normalizedQuestion: question,
  missingSlots: [],
  clarificationRound: 0,
  clarification: null,
  dataSourceIds: sourceIds,
  status: 'rejected',
  sqlValidationStatus: 'not_started',
  steps: [{ type: 'intent_classification', status: 'completed', summary: '已识别为非安全写操作请求', durationMs: 24 }],
  selectedObjects: [],
  sql: null,
  result: null,
  answer: null,
  chart: null,
  followUpQuestions: [],
  modelName: '经营分析模型',
  tokenUsage: { promptTokens: 96, completionTokens: 18, totalTokens: 114 },
  currentVersionNo: null,
  durationMs: 24,
  error: { code: 'UNSAFE_REQUEST', message: '仅支持只读经营数据查询，不能执行删除或其他写操作。', requestId: `mock-${executionId.slice(0, 8)}` },
  createdAt: now,
  completedAt: now,
});

export const executions = new Map<string, ExecutionDetail>([
  [ids.execution, createCompletedExecution(ids.execution, ids.session, ids.userMessage, '2026年商业目标最高的5个经营单元', [ids.sourceLedger])],
]);

export let applicationConfig: ApplicationConfig = {
  greetingEnabled: true,
  greetingText: '欢迎使用智能问数。选择数据源后，可以直接询问经营目标、收入趋势和完成率。',
  recommendedQuestions: ['2026年商业目标最高的5个经营单元', '北京代表处2026年1到5月收入趋势', '各产品线收入占比'],
  followUpEnabled: true,
  frequentQuestionsEnabled: true,
  frequentQuestionThreshold: 3,
  modelQaEnabled: true,
  ttsEnabled: false,
  sttEnabled: false,
  version: 1,
  updatedAt: now,
};

export let models: ModelConfig[] = [
  {
    id: ids.model,
    name: '经营分析模型',
    provider: 'openai_compatible',
    protocol: 'responses',
    baseUrl: 'https://api.example.com/v1',
    modelName: 'business-analyst-v1',
    apiKeyMask: 'sk-****demo',
    timeoutSeconds: 30,
    enabled: true,
    isActive: true,
    lastTestStatus: 'success',
    lastTestedAt: now,
    createdAt: now,
    updatedAt: now,
  },
];

export let feedbackItems: FeedbackDetail[] = [
  {
    id: ids.feedback,
    userId: 'demo-user',
    sessionId: ids.session,
    assistantMessageId: ids.assistantMessage,
    executionId: ids.execution,
    question: '2026年商业目标最高的5个经营单元',
    reason: 'metric_error',
    description: '请确认商业目标口径是否包含商解目标。',
    status: 'pending',
    version: 1,
    createdAt: now,
    updatedAt: now,
    dataSourceNames: ['经营目标台账'],
    sql: executions.get(ids.execution)?.sql ?? null,
    resultSummary: '返回5个经营单元，按商业目标降序。',
    modelName: '经营分析模型',
    answer: executions.get(ids.execution)?.answer ?? '',
    resolutionNote: null,
  },
];

export const mockStore = {
  get sessions() { return sessions; },
  set sessions(value: Session[]) { sessions = value; },
  get applicationConfig() { return applicationConfig; },
  set applicationConfig(value: ApplicationConfig) { applicationConfig = value; },
  get models() { return models; },
  set models(value: ModelConfig[]) { models = value; },
  get feedbackItems() { return feedbackItems; },
  set feedbackItems(value: FeedbackDetail[]) { feedbackItems = value; },
};

const awaitingSnapshotKey = 'management-star-mock-awaiting-execution';

interface AwaitingExecutionSnapshot {
  session: Session;
  messages: Message[];
  execution: ExecutionDetail;
}

export function persistAwaitingExecution(execution: ExecutionDetail): void {
  if (typeof sessionStorage === 'undefined' || execution.status !== 'awaiting_input') return;
  const session = sessions.find((item) => item.id === execution.sessionId);
  if (!session) return;
  const snapshot: AwaitingExecutionSnapshot = {
    session,
    messages: messagesBySession.get(execution.sessionId) ?? [],
    execution,
  };
  sessionStorage.setItem(awaitingSnapshotKey, JSON.stringify(snapshot));
}

export function restoreAwaitingExecution(): void {
  if (typeof sessionStorage === 'undefined') return;
  const serialized = sessionStorage.getItem(awaitingSnapshotKey);
  if (!serialized) return;
  try {
    const snapshot = JSON.parse(serialized) as AwaitingExecutionSnapshot;
    if (snapshot.execution.status !== 'awaiting_input' || snapshot.execution.sql || snapshot.execution.result) {
      sessionStorage.removeItem(awaitingSnapshotKey);
      return;
    }
    if (!sessions.some((item) => item.id === snapshot.session.id)) sessions = [snapshot.session, ...sessions];
    messagesBySession.set(snapshot.session.id, snapshot.messages);
    executions.set(snapshot.execution.id, snapshot.execution);
  } catch {
    sessionStorage.removeItem(awaitingSnapshotKey);
  }
}

export function clearPersistedExecution(executionId: string): void {
  if (typeof sessionStorage === 'undefined') return;
  const serialized = sessionStorage.getItem(awaitingSnapshotKey);
  if (!serialized) return;
  try {
    const snapshot = JSON.parse(serialized) as AwaitingExecutionSnapshot;
    if (snapshot.execution.id === executionId) sessionStorage.removeItem(awaitingSnapshotKey);
  } catch {
    sessionStorage.removeItem(awaitingSnapshotKey);
  }
}
