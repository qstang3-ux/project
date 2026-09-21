import { delay, http, HttpResponse } from 'msw';
import type {
  ApplicationConfigUpdate,
  AnswerVersion,
  ClarificationSubmit,
  FeedbackCreate,
  FeedbackUpdate,
  ModelConfigCreate,
  ModelConfigUpdate,
  MessageResubmitRequest,
  QueryAccepted,
  QueryCreate,
  RegenerateRequest,
  SessionCreate,
  SessionUpdate,
  ExecutionDetail,
  ExecutionEvent,
  FavoriteCreate,
  FavoriteQuestion,
} from '../api/types';
import {
  createCompletedExecution,
  createAwaitingClarificationExecution,
  createClarificationCompletedExecution,
  createRejectedExecution,
  clearPersistedExecution,
  dataSources,
  executions,
  messagesBySession,
  mockStore,
  persistAwaitingExecution,
  restoreAwaitingExecution,
} from './data';

const base = '/api/v1';
const timestamp = () => new Date().toISOString();
const clarificationResponses = new Map<string, QueryAccepted>();
let favoriteQuestions: FavoriteQuestion[] = [];
interface MockEventPlan {
  events: ExecutionEvent[];
  finalExecution: ExecutionDetail;
  disconnectOnce: boolean;
  expireCursorOnce: boolean;
  cursorExpired: boolean;
  connectionCount: number;
}
const eventPlans = new Map<string, MockEventPlan>();
const regenerationRootByExecution = new Map<string, string>();
const page = (total: number, pageNumber = 1, pageSize = 20) => ({
  page: pageNumber,
  pageSize,
  total,
  hasMore: pageNumber * pageSize < total,
});

export const handlers = [
  http.get(`${base}/data-sources`, async () => {
    await delay(180);
    return HttpResponse.json({ items: dataSources, maxSelection: 8 });
  }),
  http.get(`${base}/qa/sessions`, async () => {
    restoreAwaitingExecution();
    await delay(160);
    const items = [...mockStore.sessions].sort((left, right) => {
      if (left.pinned !== right.pinned) return left.pinned ? -1 : 1;
      return right.updatedAt.localeCompare(left.updatedAt);
    });
    return HttpResponse.json({ items, page: page(items.length, 1, 50) });
  }),
  http.post(`${base}/qa/sessions`, async ({ request }) => {
    const body = await request.json() as SessionCreate;
    const created = {
      id: crypto.randomUUID(),
      title: body.title ?? '新对话',
      pinned: false,
      messageCount: 0,
      lastMessagePreview: null,
      createdAt: timestamp(),
      updatedAt: timestamp(),
    };
    mockStore.sessions = [created, ...mockStore.sessions];
    messagesBySession.set(created.id, []);
    return HttpResponse.json(created, { status: 201 });
  }),
  http.patch(`${base}/qa/sessions/:sessionId`, async ({ params, request }) => {
    const body = await request.json() as SessionUpdate;
    const id = String(params.sessionId);
    const existing = mockStore.sessions.find((item) => item.id === id);
    if (!existing) return notFound();
    const updated = { ...existing, ...body, updatedAt: timestamp() };
    mockStore.sessions = mockStore.sessions.map((item) => item.id === id ? updated : item);
    return HttpResponse.json(updated);
  }),
  http.delete(`${base}/qa/sessions/:sessionId`, ({ params }) => {
    const id = String(params.sessionId);
    mockStore.sessions = mockStore.sessions.filter((item) => item.id !== id);
    messagesBySession.delete(id);
    const execution = [...executions.values()].find((item) => item.sessionId === id);
    if (execution) clearPersistedExecution(execution.id);
    return new HttpResponse(null, { status: 204 });
  }),
  http.get(`${base}/qa/sessions/:sessionId/messages`, async ({ params }) => {
    restoreAwaitingExecution();
    await delay(120);
    return HttpResponse.json({ items: messagesBySession.get(String(params.sessionId)) ?? [], hasMore: false, nextCursor: null });
  }),
  http.post(`${base}/qa/sessions/:sessionId/queries`, async ({ params, request }) => {
    const sessionId = String(params.sessionId);
    const body = await request.json() as QueryCreate;
    const userMessageId = crypto.randomUUID();
    const executionId = crypto.randomUUID();
    const createdAt = timestamp();
    const current = messagesBySession.get(sessionId) ?? [];
    const finalExecution = body.question.includes('删除所有订单')
      ? createRejectedExecution(executionId, sessionId, userMessageId, body.question, body.dataSourceIds)
      : body.question.includes('达成情况') || body.question.includes('今年销售额怎么样')
        ? createAwaitingClarificationExecution(executionId, sessionId, userMessageId, body.question, body.dataSourceIds)
        : createCompletedExecution(executionId, sessionId, userMessageId, body.question, body.dataSourceIds);
    const disconnectOnce = body.question.includes('SSE断线恢复') || body.question.includes('SSE游标过期');
    const execution = disconnectOnce && finalExecution.status === 'completed'
      ? { ...finalExecution, status: 'running' as const, assistantMessageId: null, result: null, answer: null, chart: null, followUpQuestions: [], completedAt: null }
      : finalExecution;
    messagesBySession.set(sessionId, [
      ...current,
      { id: userMessageId, sessionId, role: 'user', content: body.question, executionId, executionStatus: execution.status, createdAt },
    ]);
    executions.set(executionId, execution);
    eventPlans.set(executionId, {
      events: createExecutionEvents(finalExecution),
      finalExecution,
      disconnectOnce,
      expireCursorOnce: body.question.includes('SSE游标过期'),
      cursorExpired: false,
      connectionCount: 0,
    });
    persistAwaitingExecution(execution);
    const session = mockStore.sessions.find((item) => item.id === sessionId);
    if (session) {
      const updated = {
        ...session,
        title: session.messageCount === 0 ? body.question.slice(0, 28) : session.title,
        lastMessagePreview: body.question,
        messageCount: session.messageCount + 1,
        updatedAt: createdAt,
      };
      mockStore.sessions = mockStore.sessions.map((item) => item.id === sessionId ? updated : item);
    }
    await delay(350);
    return HttpResponse.json({
      sessionId,
      userMessageId,
      executionId,
      status: 'queued',
      eventUrl: `/api/v1/qa/executions/${executionId}/events`,
    }, { status: 202 });
  }),
  http.get(`${base}/qa/executions/:executionId/events`, ({ params, request }) => {
    const executionId = String(params.executionId);
    const plan = eventPlans.get(executionId);
    if (!plan) return notFound();
    const lastEventId = new URL(request.url).searchParams.get('lastEventId');
    plan.connectionCount += 1;
    if (lastEventId && plan.expireCursorOnce && !plan.cursorExpired) {
      plan.cursorExpired = true;
      return eventError(410, 'SSE_EVENT_EXPIRED', 'SSE 事件游标已超过保留期。');
    }
    const cursor = parseMockEventCursor(executionId, lastEventId, plan.events);
    if (cursor instanceof Response) return cursor;
    const replay = plan.events.slice(cursor);
    const requiresCursor = plan.disconnectOnce && !lastEventId && !(plan.expireCursorOnce && plan.cursorExpired);
    const eventCount = requiresCursor ? Math.min(2, replay.length) : replay.length;
    const delivered = replay.slice(0, eventCount);
    if (delivered.some((event) => event.type === 'answer.completed' || event.type === 'execution.completed' || event.type === 'execution.failed')) {
      executions.set(executionId, plan.finalExecution);
    }
    return new HttpResponse(delivered.map(formatMockEvent).join(''), {
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        Connection: 'keep-alive',
      },
    });
  }),
  http.get(`${base}/qa/executions/:executionId`, async ({ params }) => {
    restoreAwaitingExecution();
    await delay(550);
    const execution = executions.get(String(params.executionId));
    if (!execution) return notFound();
    const items = messagesBySession.get(execution.sessionId) ?? [];
    const terminalWithAnswer = execution.status === 'completed' || execution.status === 'rejected' || execution.status === 'failed';
    if (terminalWithAnswer && !items.some((item) => item.role === 'assistant' && item.executionId === execution.id)) {
      const userItems = items.map((item) => item.executionId === execution.id ? { ...item, executionStatus: execution.status } : item);
      messagesBySession.set(execution.sessionId, [
        ...userItems,
        {
          id: execution.assistantMessageId ?? crypto.randomUUID(),
          sessionId: execution.sessionId,
          role: 'assistant',
          content: execution.answer ?? execution.error?.message ?? '',
          sourceMessageId: execution.userMessageId,
          executionId: execution.id,
          executionStatus: execution.status,
          currentVersionNo: 1,
          createdAt: execution.completedAt ?? timestamp(),
        },
      ]);
    }
    return HttpResponse.json(execution);
  }),
  http.get(`${base}/qa/executions/:executionId/export`, ({ params }) => {
    const executionId = String(params.executionId);
    const execution = executions.get(executionId);
    if (!execution) return notFound();
    const columns = execution.result?.columns ?? [];
    const rows = execution.result?.rows ?? [];
    const escape = (value: unknown) => {
      const text = typeof value === 'string'
        ? value
        : typeof value === 'number' || typeof value === 'boolean'
          ? String(value)
          : '';
      return `"${text.replaceAll('"', '""')}"`;
    };
    const csv = [
      columns.map((column) => escape(column.label)).join(','),
      ...rows.map((row) => columns.map((column) => escape(row[column.key])).join(',')),
    ].join('\r\n');
    return new HttpResponse(`\ufeff${csv}`, {
      headers: {
        'Content-Disposition': `attachment; filename="execution-${executionId}.csv"`,
        'Content-Type': 'text/csv; charset=utf-8',
      },
    });
  }),
  http.post(`${base}/qa/executions/:executionId/clarifications`, async ({ params, request }) => {
    const executionId = String(params.executionId);
    const execution = executions.get(executionId);
    if (!execution) return notFound();
    const idempotencyKey = request.headers.get('Idempotency-Key');
    if (!idempotencyKey) return HttpResponse.json({ error: { code: 'VALIDATION_ERROR', message: '缺少 Idempotency-Key', requestId: crypto.randomUUID() } }, { status: 422 });
    const replay = clarificationResponses.get(idempotencyKey);
    if (replay) return HttpResponse.json(replay, { status: 202 });
    if (execution.status !== 'awaiting_input') {
      return HttpResponse.json({ error: { code: 'EXECUTION_NOT_AWAITING_INPUT', message: '当前执行不处于等待补充状态。', requestId: crypto.randomUUID() } }, { status: 409 });
    }
    const body = await request.json() as ClarificationSubmit;
    const supplementalMessageId = crypto.randomUUID();
    const needsSecondRound = execution.clarificationRound < 2 && (!body.content.includes('2026') || !body.content.includes('经营单元'));
    const resumed = needsSecondRound
      ? createAwaitingClarificationExecution(execution.id, execution.sessionId, execution.userMessageId, execution.question, execution.dataSourceIds, 2)
      : createClarificationCompletedExecution(execution, body.content);
    executions.set(executionId, resumed);
    const current = messagesBySession.get(execution.sessionId) ?? [];
    messagesBySession.set(execution.sessionId, [
      ...current.map((item) => item.executionId === executionId ? { ...item, executionStatus: resumed.status } : item),
      { id: supplementalMessageId, sessionId: execution.sessionId, role: 'user', content: body.content, executionId, executionStatus: resumed.status, createdAt: timestamp() },
    ]);
    const session = mockStore.sessions.find((item) => item.id === execution.sessionId);
    if (session) mockStore.sessions = mockStore.sessions.map((item) => item.id === session.id ? { ...item, lastMessagePreview: body.content, messageCount: item.messageCount + 1, updatedAt: timestamp() } : item);
    if (resumed.status === 'awaiting_input') persistAwaitingExecution(resumed);
    else clearPersistedExecution(executionId);
    await delay(250);
    const accepted: QueryAccepted = {
      sessionId: execution.sessionId,
      userMessageId: supplementalMessageId,
      executionId,
      status: 'queued',
      eventUrl: `/api/v1/qa/executions/${executionId}/events`,
    };
    clarificationResponses.set(idempotencyKey, accepted);
    return HttpResponse.json(accepted, { status: 202 });
  }),
  http.post(`${base}/qa/executions/:executionId/cancel`, ({ params }) => {
    const executionId = String(params.executionId);
    const execution = executions.get(executionId);
    if (execution) {
      executions.set(executionId, { ...execution, status: 'cancelled', clarification: null, completedAt: timestamp() });
      const items = messagesBySession.get(execution.sessionId) ?? [];
      messagesBySession.set(execution.sessionId, items.map((item) => item.executionId === executionId ? { ...item, executionStatus: 'cancelled' as const } : item));
      clearPersistedExecution(executionId);
    }
    return HttpResponse.json({ executionId, status: 'cancelled', updatedAt: timestamp() });
  }),
  http.post(`${base}/qa/messages/:messageId/resubmit`, async ({ params, request }) => {
    const messageId = String(params.messageId);
    const body = await request.json() as MessageResubmitRequest;
    const sourceEntry = [...messagesBySession.entries()].find(([, items]) =>
      items.some((item) => item.id === messageId),
    );
    if (!sourceEntry) return notFound();

    const sessionId = crypto.randomUUID();
    const userMessageId = crypto.randomUUID();
    const executionId = crypto.randomUUID();
    const createdAt = timestamp();
    const execution = createCompletedExecution(
      executionId,
      sessionId,
      userMessageId,
      body.question,
      body.dataSourceIds,
    );
    executions.set(executionId, execution);
    messagesBySession.set(sessionId, [{
      id: userMessageId,
      sessionId,
      role: 'user',
      content: body.question,
      sourceMessageId: messageId,
      executionId,
      executionStatus: 'completed',
      createdAt,
    }]);
    mockStore.sessions = [{
      id: sessionId,
      title: body.branchTitle ?? body.question.slice(0, 28),
      pinned: false,
      messageCount: 1,
      lastMessagePreview: body.question,
      createdAt,
      updatedAt: createdAt,
    }, ...mockStore.sessions];
    await delay(250);
    return HttpResponse.json({
      sessionId,
      userMessageId,
      executionId,
      status: 'queued',
      eventUrl: `/api/v1/qa/executions/${executionId}/events`,
    }, { status: 202 });
  }),
  http.post(`${base}/qa/messages/:messageId/regenerate`, async ({ params, request }) => {
    const messageId = String(params.messageId);
    const body = await request.json() as RegenerateRequest;
    const original = [...executions.values()].find((item) =>
      item.userMessageId === messageId || item.assistantMessageId === messageId,
    );
    if (!original) return notFound();

    const userMessageId = crypto.randomUUID();
    const executionId = crypto.randomUUID();
    const createdAt = timestamp();
    const execution = createCompletedExecution(
      executionId,
      original.sessionId,
      userMessageId,
      original.question,
      original.dataSourceIds,
    );
    const regenerated = {
      ...execution,
      answer: `${execution.answer ?? ''}（重新生成版本）`,
      chart: body.generateChart ? execution.chart : null,
    };
    const rootId = regenerationRootByExecution.get(original.id) ?? original.id;
    regenerationRootByExecution.set(original.id, rootId);
    regenerationRootByExecution.set(executionId, rootId);
    executions.set(executionId, regenerated);
    const current = messagesBySession.get(original.sessionId) ?? [];
    messagesBySession.set(original.sessionId, [...current, {
      id: userMessageId,
      sessionId: original.sessionId,
      role: 'user',
      content: original.question,
      executionId,
      executionStatus: 'completed',
      createdAt,
    }]);
    await delay(250);
    return HttpResponse.json({
      sessionId: original.sessionId,
      userMessageId,
      executionId,
      status: 'queued',
      eventUrl: `/api/v1/qa/executions/${executionId}/events`,
    }, { status: 202 });
  }),
  http.get(`${base}/qa/messages/:messageId/versions`, ({ params }) => {
    const messageId = String(params.messageId);
    const source = [...executions.values()].find((item) =>
      item.userMessageId === messageId || item.assistantMessageId === messageId,
    );
    if (!source) return notFound();
    const rootId = regenerationRootByExecution.get(source.id) ?? source.id;
    const lineage = [...executions.values()]
      .filter((item) => (regenerationRootByExecution.get(item.id) ?? item.id) === rootId)
      .filter((item) => item.status === 'completed' && item.answer)
      .sort((left, right) => left.createdAt.localeCompare(right.createdAt));
    const versions: AnswerVersion[] = lineage.map((item, index) => ({
      versionNo: index + 1,
      executionId: item.id,
      answer: item.answer ?? '',
      sql: item.sql,
      chart: item.chart ?? undefined,
      modelName: item.modelName,
      durationMs: item.durationMs,
      isCurrent: index === lineage.length - 1,
      createdAt: item.createdAt,
    }));
    return HttpResponse.json(versions);
  }),
  http.get(`${base}/questions/frequent`, ({ request }) => {
    const limit = Number(new URL(request.url).searchParams.get('limit') ?? 10);
    const counts = new Map<string, { count: number; lastAskedAt: string }>();
    [...messagesBySession.values()].flat().filter((item) => item.role === 'user').forEach((item) => {
      const current = counts.get(item.content);
      counts.set(item.content, { count: (current?.count ?? 0) + 1, lastAskedAt: item.createdAt });
    });
    const items = [...counts.entries()].map(([question, value]) => ({ question, ...value })).sort((left, right) => right.count - left.count).slice(0, limit);
    return HttpResponse.json(items.length ? items : [
      { question: '2026年商业目标最高的5个经营单元', count: 8, lastAskedAt: timestamp() },
      { question: '北京代表处2026年1到5月收入趋势', count: 5, lastAskedAt: timestamp() },
    ]);
  }),
  http.get(`${base}/questions/favorites`, () => HttpResponse.json(favoriteQuestions)),
  http.post(`${base}/questions/favorites`, async ({ request }) => {
    const body = await request.json() as FavoriteCreate;
    const existing = favoriteQuestions.find((item) => item.question === body.question);
    if (existing) return HttpResponse.json(existing);
    const created: FavoriteQuestion = { id: crypto.randomUUID(), question: body.question, sourceMessageId: body.sourceMessageId ?? null, createdAt: timestamp() };
    favoriteQuestions = [created, ...favoriteQuestions];
    return HttpResponse.json(created, { status: 201 });
  }),
  http.delete(`${base}/questions/favorites/:favoriteId`, ({ params }) => {
    favoriteQuestions = favoriteQuestions.filter((item) => item.id !== String(params.favoriteId));
    return new HttpResponse(null, { status: 204 });
  }),
  http.get(`${base}/qa/logs`, ({ request }) => {
    const url = new URL(request.url);
    const keyword = url.searchParams.get('keyword')?.toLowerCase() ?? '';
    const userId = url.searchParams.get('userId')?.toLowerCase() ?? '';
    const status = url.searchParams.get('status');
    const from = url.searchParams.get('from');
    const to = url.searchParams.get('to');
    const pageNumber = Number(url.searchParams.get('page') ?? 1);
    const pageSize = Number(url.searchParams.get('pageSize') ?? 20);
    const filtered = [...executions.values()].filter((item) =>
      (!keyword || item.question.toLowerCase().includes(keyword)) &&
      (!userId || 'demo-user'.includes(userId)) &&
      (!status || item.status === status) &&
      (!from || item.createdAt >= from) && (!to || item.createdAt <= to));
    const items = filtered.sort((left, right) => right.createdAt.localeCompare(left.createdAt)).map((item) => ({
      executionId: item.id, userId: 'demo-user', requestId: item.requestId, question: item.question, status: item.status,
      modelName: item.modelName ?? null, rowCount: item.result?.rowCount ?? null, durationMs: item.durationMs ?? null,
      errorCode: item.error?.code ?? null, createdAt: item.createdAt,
    }));
    const start = (pageNumber - 1) * pageSize;
    return HttpResponse.json({ items: items.slice(start, start + pageSize), page: page(items.length, pageNumber, pageSize) });
  }),
  http.get(`${base}/qa/logs/:executionId`, ({ params }) => {
    const item = executions.get(String(params.executionId));
    if (!item) return notFound();
    const modelCalls = item.modelName ? [{ provider: 'openai_compatible', model: item.modelName, purpose: 'answer_generation' as const, durationMs: item.durationMs ?? 0, promptTokens: 320, completionTokens: 96, totalTokens: 416, retryCount: 0, status: 'success' as const, errorCode: null }] : [];
    return HttpResponse.json({
      executionId: item.id, userId: 'demo-user', requestId: item.requestId, question: item.question, status: item.status,
      modelName: item.modelName ?? null, rowCount: item.result?.rowCount ?? null, durationMs: item.durationMs ?? null, errorCode: item.error?.code ?? null, createdAt: item.createdAt,
      sessionId: item.sessionId, userMessageId: item.userMessageId, assistantMessageId: item.assistantMessageId, intent: item.intent, normalizedQuestion: item.normalizedQuestion,
      missingSlots: item.missingSlots, clarificationRound: item.clarificationRound, dataSourceNames: dataSources.filter((source) => item.dataSourceIds.includes(source.id)).map((source) => source.name),
      selectedObjects: item.selectedObjects, generatedSql: item.sql, executedSql: item.sql, validationSummary: item.sqlValidationStatus,
      tokenUsage: { promptTokens: 320, completionTokens: 96, totalTokens: 416 }, modelCalls,
      graphVersion: 'langgraph-v2', graphNodeTrace: ['load_context', 'classify_intent', ...(item.sql ? ['retrieve_knowledge', 'generate_sql', 'validate_sql', 'execute_sql', 'summarize_result'] : []), 'persist_result'],
      checkpointStatus: 'completed', ragDocumentIds: [], ragDegraded: false, steps: item.steps, errorMessage: item.error?.message ?? null,
    });
  }),
  http.get(`${base}/application-config`, async () => {
    await delay(150);
    return HttpResponse.json(mockStore.applicationConfig);
  }),
  http.put(`${base}/application-config`, async ({ request }) => {
    const bodyDraft = await request.json() as Partial<ApplicationConfigUpdate>;
    const requiredFields: Array<keyof ApplicationConfigUpdate> = [
      'greetingEnabled', 'greetingText', 'recommendedQuestions', 'followUpEnabled',
      'frequentQuestionsEnabled', 'frequentQuestionThreshold', 'modelQaEnabled',
      'ttsEnabled', 'sttEnabled', 'version',
    ];
    if (requiredFields.some((field) => bodyDraft[field] === undefined)) {
      return HttpResponse.json({ error: { code: 'VALIDATION_ERROR', message: '应用配置字段不完整', requestId: crypto.randomUUID() } }, { status: 422 });
    }
    const body = bodyDraft as ApplicationConfigUpdate;
    if (body.version !== mockStore.applicationConfig.version) return conflict();
    mockStore.applicationConfig = { ...body, version: body.version + 1, updatedAt: timestamp() };
    return HttpResponse.json(mockStore.applicationConfig);
  }),
  http.get(`${base}/model-configs`, async () => {
    await delay(150);
    return HttpResponse.json(mockStore.models);
  }),
  http.post(`${base}/model-configs`, async ({ request }) => {
    const body = await request.json() as ModelConfigCreate;
    const created = {
      id: crypto.randomUUID(),
      name: body.name,
      provider: body.provider,
      protocol: body.protocol,
      baseUrl: body.baseUrl,
      modelName: body.modelName,
      apiKeyMask: `****${body.apiKey.slice(-4)}`,
      timeoutSeconds: body.timeoutSeconds,
      enabled: body.enabled,
      isActive: false,
      lastTestStatus: null,
      lastTestedAt: null,
      createdAt: timestamp(),
      updatedAt: timestamp(),
    };
    mockStore.models = [...mockStore.models, created];
    return HttpResponse.json(created, { status: 201 });
  }),
  http.post(`${base}/model-configs/test`, async () => {
    await delay(700);
    return HttpResponse.json({ success: true, status: 'success', message: '连接成功，模型可用。', durationMs: 684 });
  }),
  http.patch(`${base}/model-configs/:id`, async ({ params, request }) => {
    const id = String(params.id);
    const body = await request.json() as ModelConfigUpdate;
    const current = mockStore.models.find((model) => model.id === id);
    if (!current) return notFound();
    const updated = {
      ...current,
      ...(body.name !== undefined ? { name: body.name } : {}),
      ...(body.protocol !== undefined ? { protocol: body.protocol } : {}),
      ...(body.baseUrl !== undefined ? { baseUrl: body.baseUrl } : {}),
      ...(body.modelName !== undefined ? { modelName: body.modelName } : {}),
      ...(body.timeoutSeconds !== undefined ? { timeoutSeconds: body.timeoutSeconds } : {}),
      ...(body.enabled !== undefined ? { enabled: body.enabled } : {}),
      ...(body.apiKey ? { apiKeyMask: `****${body.apiKey.slice(-4)}` } : {}),
      updatedAt: timestamp(),
    };
    mockStore.models = mockStore.models.map((model) => model.id === id ? updated : model);
    return HttpResponse.json(updated);
  }),
  http.post(`${base}/model-configs/:id/activate`, ({ params }) => {
    const id = String(params.id);
    mockStore.models = mockStore.models.map((model) => ({ ...model, isActive: model.id === id, updatedAt: timestamp() }));
    const active = mockStore.models.find((model) => model.id === id);
    return active ? HttpResponse.json(active) : notFound();
  }),
  http.delete(`${base}/model-configs/:id`, ({ params }) => {
    const id = String(params.id);
    const target = mockStore.models.find((model) => model.id === id);
    if (!target) return notFound();
    if (target.isActive) return conflict('当前模型不能删除，请先启用其他模型。');
    mockStore.models = mockStore.models.filter((model) => model.id !== id);
    return new HttpResponse(null, { status: 204 });
  }),
  http.get(`${base}/feedback`, ({ request }) => {
    const url = new URL(request.url);
    const keyword = url.searchParams.get('keyword')?.toLowerCase() ?? '';
    const userId = url.searchParams.get('userId')?.toLowerCase() ?? '';
    const status = url.searchParams.get('status');
    const reason = url.searchParams.get('reason');
    const pageNumber = Number(url.searchParams.get('page') ?? 1);
    const pageSize = Number(url.searchParams.get('pageSize') ?? 20);
    const filtered = mockStore.feedbackItems.filter((item) =>
      (!keyword || item.question.toLowerCase().includes(keyword)) &&
      (!userId || item.userId.toLowerCase().includes(userId)) &&
      (!status || item.status === status) &&
      (!reason || item.reason === reason));
    return HttpResponse.json({ items: filtered, page: page(filtered.length, pageNumber, pageSize) });
  }),
  http.post(`${base}/feedback`, async ({ request }) => {
    const body = await request.json() as FeedbackCreate;
    const execution = executions.get(body.executionId);
    if (!execution) return notFound();
    const created = {
      id: crypto.randomUUID(),
      userId: 'demo-user',
      ...body,
      question: execution.question,
      answer: execution.answer ?? '',
      reason: body.reason,
      description: body.description ?? null,
      status: 'pending' as const,
      version: 1,
      createdAt: timestamp(),
      updatedAt: timestamp(),
      dataSourceNames: dataSources.filter((source) => execution.dataSourceIds.includes(source.id)).map((source) => source.name),
      sql: execution.sql ?? null,
      resultSummary: `查询返回 ${String(execution.result?.rowCount ?? 0)} 行`,
      modelName: execution.modelName ?? null,
      resolutionNote: null,
    };
    mockStore.feedbackItems = [created, ...mockStore.feedbackItems];
    return HttpResponse.json(created, { status: 201 });
  }),
  http.get(`${base}/feedback/:id`, ({ params }) => {
    const item = mockStore.feedbackItems.find((feedback) => feedback.id === String(params.id));
    return item ? HttpResponse.json(item) : notFound();
  }),
  http.patch(`${base}/feedback/:id`, async ({ params, request }) => {
    const body = await request.json() as FeedbackUpdate;
    const item = mockStore.feedbackItems.find((feedback) => feedback.id === String(params.id));
    if (!item) return notFound();
    if (item.version !== body.version) return conflict();
    const updated = { ...item, status: body.status, resolutionNote: body.resolutionNote ?? null, version: item.version + 1, updatedAt: timestamp() };
    mockStore.feedbackItems = mockStore.feedbackItems.map((feedback) => feedback.id === item.id ? updated : feedback);
    return HttpResponse.json(updated);
  }),
];

function createExecutionEvents(execution: ExecutionDetail): ExecutionEvent[] {
  const occurredAt = timestamp();
  const events: Array<Omit<ExecutionEvent, 'id'>> = [
    { executionId: execution.id, type: 'execution.started', status: 'running', summary: '开始执行', occurredAt, data: { kind: 'execution.started' } },
  ];
  if (execution.status === 'awaiting_input' && execution.clarification) {
    events.push({ executionId: execution.id, type: 'clarification.required', status: 'awaiting_input', summary: execution.clarification.prompt, occurredAt, data: { kind: 'clarification.required', clarification: execution.clarification } });
  } else if (execution.status === 'completed') {
    events.push(
      { executionId: execution.id, type: 'schema.selected', status: 'running', summary: '数据对象已选择', occurredAt, data: { kind: 'schema.selected', selectedObjects: execution.selectedObjects ?? [] } },
      { executionId: execution.id, type: 'sql.generated', status: 'running', summary: 'SQL 已生成', occurredAt, data: { kind: 'sql.generated', sqlAvailable: Boolean(execution.sql) } },
      { executionId: execution.id, type: 'sql.validated', status: 'running', summary: 'SQL 校验完成', occurredAt, data: { kind: 'sql.validated', sqlValidationStatus: execution.sqlValidationStatus, ruleVersion: 'mock-v1' } },
      { executionId: execution.id, type: 'query.completed', status: 'running', summary: '查询完成', occurredAt, data: { kind: 'query.completed', rowCount: execution.result?.rowCount ?? 0, truncated: execution.result?.truncated ?? false } },
      { executionId: execution.id, type: 'answer.completed', status: 'running', summary: '回答生成完成', occurredAt, data: { kind: 'answer.completed', assistantMessageId: execution.assistantMessageId } },
      { executionId: execution.id, type: 'execution.completed', status: 'completed', summary: '执行完成', occurredAt, data: { kind: 'execution.completed', assistantMessageId: execution.assistantMessageId } },
    );
  } else {
    events.push({ executionId: execution.id, type: 'execution.failed', status: execution.status, summary: execution.error?.message ?? '执行失败', occurredAt, data: { kind: 'execution.failed', error: execution.error ?? { code: 'QUERY_FAILED', message: '执行失败', requestId: execution.requestId } } });
  }
  return events.map((event, index) => ({ ...event, id: `${execution.id}:${String(index + 1)}` }));
}

function formatMockEvent(event: ExecutionEvent) {
  return `id: ${event.id}\nevent: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
}

function parseMockEventCursor(executionId: string, lastEventId: string | null, events: ExecutionEvent[]): number | Response {
  if (!lastEventId) return 0;
  const separator = lastEventId.lastIndexOf(':');
  if (separator < 1) return eventError(422, 'SSE_EVENT_ID_INVALID', 'SSE 事件游标格式非法。');
  const cursorExecutionId = lastEventId.slice(0, separator);
  const sequence = Number(lastEventId.slice(separator + 1));
  if (cursorExecutionId !== executionId) return eventError(409, 'SSE_EVENT_EXECUTION_MISMATCH', 'SSE 事件游标属于其他执行。');
  if (!Number.isInteger(sequence) || sequence < 0 || sequence > events.length) return eventError(422, 'SSE_EVENT_ID_INVALID', 'SSE 事件游标序号非法。');
  return sequence;
}

function eventError(status: number, code: string, message: string) {
  return HttpResponse.json({ error: { code, message, requestId: crypto.randomUUID() } }, { status });
}

function notFound() {
  return HttpResponse.json({ error: { code: 'RESOURCE_NOT_FOUND', message: '资源不存在', requestId: crypto.randomUUID() } }, { status: 404 });
}

function conflict(message = '数据版本冲突，请刷新后重试。') {
  return HttpResponse.json({ error: { code: 'VERSION_CONFLICT', message, requestId: crypto.randomUUID() } }, { status: 409 });
}
