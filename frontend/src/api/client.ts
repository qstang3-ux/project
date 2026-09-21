import type {
  ApplicationConfig,
  ApplicationConfigUpdate,
  AnswerVersion,
  ClarificationSubmit,
  DataSourceListResponse,
  ErrorDetail,
  ExecutionDetail,
  FeedbackCreate,
  FeedbackDetail,
  FeedbackListResponse,
  FeedbackUpdate,
  FavoriteCreate,
  FavoriteQuestion,
  FrequentQuestion,
  MessageListResponse,
  MessageResubmitRequest,
  ModelConfig,
  ModelConfigCreate,
  ModelConfigUpdate,
  QueryAccepted,
  QueryCreate,
  RegenerateRequest,
  QaLogDetail,
  QaLogListResponse,
  Session,
  SessionCreate,
  SessionListResponse,
  SessionUpdate,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export type ExecutionEventCursorCheck = 'valid' | 'reset' | 'unavailable';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string;
  readonly details: Record<string, unknown> | null;

  constructor(status: number, error: ErrorDetail) {
    super(error.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = error.code;
    this.requestId = error.requestId;
    this.details = error.details ?? null;
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & { body?: unknown };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  if (options.body !== undefined) headers.set('Content-Type', 'application/json');

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(0, {
      code: 'NETWORK_ERROR',
      message: '无法连接服务，请检查网络后重试。',
      requestId: 'client-network-error',
    });
  }

  if (!response.ok) {
    const fallback: ErrorDetail = {
      code: 'INTERNAL_ERROR',
      message: '服务暂时不可用，请稍后重试。',
      requestId: response.headers.get('x-request-id') ?? 'unknown',
    };
    const payload = (await response.json().catch(() => null)) as { error?: ErrorDetail } | null;
    throw new ApiError(response.status, payload?.error ?? fallback);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function download(path: string): Promise<{ blob: Blob; filename: string }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { headers: { Accept: 'text/csv' } });
  } catch {
    throw new ApiError(0, {
      code: 'NETWORK_ERROR',
      message: '无法连接服务，请检查网络后重试。',
      requestId: 'client-network-error',
    });
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error?: ErrorDetail } | null;
    throw new ApiError(response.status, payload?.error ?? {
      code: 'INTERNAL_ERROR',
      message: '导出失败，请稍后重试。',
      requestId: response.headers.get('x-request-id') ?? 'unknown',
    });
  }
  const disposition = response.headers.get('content-disposition') ?? '';
  const matched = /filename="?([^";]+)"?/i.exec(disposition);
  return { blob: await response.blob(), filename: matched?.[1] ?? 'query-result.csv' };
}

function queryString(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : '';
}

export const api = {
  listDataSources: () => request<DataSourceListResponse>('/data-sources'),
  listSessions: () => request<SessionListResponse>('/qa/sessions?page=1&pageSize=50'),
  createSession: (body: SessionCreate = {}) => request<Session>('/qa/sessions', { method: 'POST', body }),
  updateSession: (id: string, body: SessionUpdate) =>
    request<Session>(`/qa/sessions/${id}`, { method: 'PATCH', body }),
  deleteSession: (id: string) => request<undefined>(`/qa/sessions/${id}`, { method: 'DELETE' }),
  listMessages: (sessionId: string) =>
    request<MessageListResponse>(`/qa/sessions/${sessionId}/messages?limit=100`),
  createQuery: (sessionId: string, body: QueryCreate) =>
    request<QueryAccepted>(`/qa/sessions/${sessionId}/queries`, {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body,
    }),
  resubmitMessage: (messageId: string, body: MessageResubmitRequest) =>
    request<QueryAccepted>(`/qa/messages/${messageId}/resubmit`, {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body,
    }),
  regenerateAnswer: (messageId: string, body: RegenerateRequest = { generateChart: true }) =>
    request<QueryAccepted>(`/qa/messages/${messageId}/regenerate`, {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body,
    }),
  listAnswerVersions: (messageId: string) => request<AnswerVersion[]>(`/qa/messages/${messageId}/versions`),
  getExecution: (executionId: string) => request<ExecutionDetail>(`/qa/executions/${executionId}`),
  exportExecutionCsv: (executionId: string) => download(`/qa/executions/${executionId}/export`),
  submitClarification: (executionId: string, body: ClarificationSubmit, idempotencyKey: string) =>
    request<QueryAccepted>(`/qa/executions/${executionId}/clarifications`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body,
    }),
  executionEventsUrl: (executionId: string, lastEventId?: string) => {
    const cursor = lastEventId ? `?${new URLSearchParams({ lastEventId }).toString()}` : '';
    return `${API_BASE_URL}/qa/executions/${executionId}/events${cursor}`;
  },
  checkExecutionEventCursor: async (executionId: string, lastEventId: string): Promise<ExecutionEventCursorCheck> => {
    try {
      const response = await fetch(`${API_BASE_URL}/qa/executions/${executionId}/events?${new URLSearchParams({ lastEventId }).toString()}`, {
        headers: { Accept: 'text/event-stream' },
      });
      if (response.ok) {
        await response.body?.cancel();
        return 'valid';
      }
      const payload = (await response.json().catch(() => null)) as { error?: ErrorDetail } | null;
      const code = payload?.error?.code;
      if (response.status === 410 || code === 'SSE_EVENT_EXPIRED' || code === 'SSE_EVENT_ID_INVALID' || code === 'SSE_EVENT_EXECUTION_MISMATCH') return 'reset';
      return 'unavailable';
    } catch {
      return 'unavailable';
    }
  },
  cancelExecution: (executionId: string) =>
    request(`/qa/executions/${executionId}/cancel`, { method: 'POST' }),
  listFrequentQuestions: (limit = 10) => request<FrequentQuestion[]>(`/questions/frequent?limit=${String(limit)}`),
  listFavorites: () => request<FavoriteQuestion[]>('/questions/favorites'),
  addFavorite: (body: FavoriteCreate) => request<FavoriteQuestion>('/questions/favorites', { method: 'POST', body }),
  removeFavorite: (favoriteId: string) => request<undefined>(`/questions/favorites/${favoriteId}`, { method: 'DELETE' }),
  listQaLogs: (filters: { page: number; pageSize: number; keyword?: string; status?: string; userId?: string; from?: string; to?: string }) =>
    request<QaLogListResponse>(`/qa/logs${queryString(filters)}`),
  getQaLog: (executionId: string) => request<QaLogDetail>(`/qa/logs/${executionId}`),
  getApplicationConfig: () => request<ApplicationConfig>('/application-config'),
  updateApplicationConfig: (body: ApplicationConfigUpdate) =>
    request<ApplicationConfig>('/application-config', { method: 'PUT', body }),
  listModels: () => request<ModelConfig[]>('/model-configs'),
  createModel: (body: ModelConfigCreate) => request<ModelConfig>('/model-configs', { method: 'POST', body }),
  updateModel: (id: string, body: ModelConfigUpdate) =>
    request<ModelConfig>(`/model-configs/${id}`, { method: 'PATCH', body }),
  deleteModel: (id: string) => request<undefined>(`/model-configs/${id}`, { method: 'DELETE' }),
  activateModel: (id: string) => request<ModelConfig>(`/model-configs/${id}/activate`, { method: 'POST' }),
  testModel: (body: Record<string, unknown>) =>
    request<{ success: boolean; status: string; message: string; durationMs: number }>('/model-configs/test', {
      method: 'POST', body,
    }),
  listFeedback: (filters: { page: number; pageSize: number; keyword?: string; status?: string; reason?: string; userId?: string }) =>
    request<FeedbackListResponse>(`/feedback${queryString(filters)}`),
  createFeedback: (body: FeedbackCreate) => request<FeedbackDetail>('/feedback', { method: 'POST', body }),
  getFeedback: (id: string) => request<FeedbackDetail>(`/feedback/${id}`),
  updateFeedback: (id: string, body: FeedbackUpdate) =>
    request<FeedbackDetail>(`/feedback/${id}`, { method: 'PATCH', body }),
};
