import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from './client';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('checkExecutionEventCursor', () => {
  it('resets the stream when the server reports an expired cursor', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: {
        code: 'SSE_EVENT_EXPIRED',
        message: 'SSE 事件游标已超过保留期。',
        requestId: 'request-expired',
      },
    }), { status: 410, headers: { 'Content-Type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.checkExecutionEventCursor('execution-a', 'execution-a:2')).resolves.toBe('reset');
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/qa/executions/execution-a/events?lastEventId=execution-a%3A2', {
      headers: { Accept: 'text/event-stream' },
    });
  });
});
