import { describe, expect, it, vi } from 'vitest';
import { ExecutionEventStream } from './executionEventStream';

class FakeEventSource {
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  private readonly listeners = new Map<string, Set<EventListener>>();

  addEventListener(type: string, listener: EventListener) {
    const entries = this.listeners.get(type) ?? new Set<EventListener>();
    entries.add(listener);
    this.listeners.set(type, entries);
  }

  removeEventListener(type: string, listener: EventListener) {
    this.listeners.get(type)?.delete(listener);
  }

  close() {
    this.closed = true;
  }

  emit(type: string, id: string) {
    const event = new MessageEvent(type, { data: JSON.stringify({ id, type }), lastEventId: id });
    this.listeners.get(type)?.forEach((listener) => listener(event));
  }

  fail() {
    this.onerror?.();
  }

  listenerCount() {
    return [...this.listeners.values()].reduce((total, entries) => total + entries.size, 0);
  }
}

function createHarness(checkCursor: () => Promise<'valid' | 'reset' | 'unavailable'> = () => Promise.resolve('valid')) {
  const sources: FakeEventSource[] = [];
  const urls: string[] = [];
  const scheduled: Array<() => void> = [];
  const refresh = vi.fn();
  const stream = new ExecutionEventStream({
    executionId: 'execution-a',
    initialStatus: 'running',
    refresh,
    createEventSource: (url) => {
      urls.push(url);
      const source = new FakeEventSource();
      sources.push(source);
      return source;
    },
    eventsUrl: (executionId, lastEventId) => `/events/${executionId}${lastEventId ? `?lastEventId=${encodeURIComponent(lastEventId)}` : ''}`,
    checkCursor: async () => checkCursor(),
    schedule: (callback) => {
      scheduled.push(callback);
      return scheduled.length as unknown as ReturnType<typeof setTimeout>;
    },
    cancelSchedule: vi.fn(),
    reconnectDelays: [1, 2, 3],
  });
  return { stream, sources, urls, scheduled, refresh };
}

function createWaitingHarness() {
  const sources: FakeEventSource[] = [];
  const stream = new ExecutionEventStream({
    executionId: 'execution-a',
    refresh: vi.fn(),
    createEventSource: () => {
      const source = new FakeEventSource();
      sources.push(source);
      return source;
    },
    eventsUrl: () => '/events/execution-a',
    checkCursor: () => Promise.resolve('valid'),
  });
  return { stream, sources };
}

async function runNext(callbacks: Array<() => void>) {
  callbacks.shift()?.();
  await Promise.resolve();
  await Promise.resolve();
}

function sourceAt(sources: FakeEventSource[], index: number) {
  const source = sources[index];
  if (!source) throw new Error(`Missing fake EventSource at index ${String(index)}`);
  return source;
}

describe('ExecutionEventStream', () => {
  it('waits for a streamable status before opening a connection', () => {
    const { stream, sources } = createWaitingHarness();
    expect(sources).toHaveLength(0);

    stream.updateStatus('running');
    expect(sources).toHaveLength(1);
    stream.dispose();
  });

  it('deduplicates event IDs and closes on terminal events', () => {
    const { sources, refresh } = createHarness();
    sourceAt(sources, 0).emit('schema.selected', 'execution-a:1');
    sourceAt(sources, 0).emit('schema.selected', 'execution-a:1');
    sourceAt(sources, 0).emit('execution.completed', 'execution-a:2');

    expect(refresh).toHaveBeenCalledTimes(2);
    expect(sourceAt(sources, 0).closed).toBe(true);
  });

  it('reconnects at most three times after consecutive failures', async () => {
    const { sources, scheduled } = createHarness();
    for (let index = 0; index < 4; index += 1) {
      sourceAt(sources, index).fail();
      await runNext(scheduled);
    }

    expect(sources).toHaveLength(4);
    expect(scheduled).toHaveLength(0);
  });

  it('uses the last event ID on reconnect and resets an expired cursor', async () => {
    const { sources, urls, scheduled, refresh } = createHarness(() => Promise.resolve('reset'));
    sourceAt(sources, 0).emit('sql.generated', 'execution-a:7');
    sourceAt(sources, 0).fail();
    await runNext(scheduled);

    expect(refresh).toHaveBeenCalledTimes(2);
    expect(urls).toEqual(['/events/execution-a', '/events/execution-a']);
  });

  it('passes the stable last event ID through the reconnect query', async () => {
    const { sources, urls, scheduled } = createHarness();
    sourceAt(sources, 0).emit('sql.generated', 'execution-a:7');
    sourceAt(sources, 0).fail();
    await runNext(scheduled);

    expect(urls[1]).toBe('/events/execution-a?lastEventId=execution-a%3A7');
  });

  it('isolates cursor and listeners when executions switch', () => {
    const first = createHarness();
    sourceAt(first.sources, 0).emit('schema.selected', 'execution-a:1');
    first.stream.dispose();
    const second = createHarness();
    sourceAt(first.sources, 0).emit('sql.generated', 'execution-a:2');
    sourceAt(second.sources, 0).emit('schema.selected', 'execution-a:1');

    expect(sourceAt(first.sources, 0).closed).toBe(true);
    expect(sourceAt(first.sources, 0).listenerCount()).toBe(0);
    expect(sourceAt(first.sources, 0).onerror).toBeNull();
    expect(first.refresh).toHaveBeenCalledTimes(1);
    expect(second.refresh).toHaveBeenCalledTimes(1);
    second.stream.dispose();
  });

  it('cancels scheduled and in-flight reconnect work on dispose', async () => {
    let resolveCursor: ((result: 'valid') => void) | undefined;
    const cursorCheck = new Promise<'valid'>((resolve) => { resolveCursor = resolve; });
    const { stream, sources, scheduled } = createHarness(() => cursorCheck);
    sourceAt(sources, 0).emit('sql.generated', 'execution-a:4');
    sourceAt(sources, 0).fail();
    scheduled.shift()?.();
    await Promise.resolve();
    stream.dispose();
    resolveCursor?.('valid');
    await Promise.resolve();
    await Promise.resolve();

    expect(sources).toHaveLength(1);
    expect(sourceAt(sources, 0).listenerCount()).toBe(0);
    expect(sourceAt(sources, 0).onerror).toBeNull();
  });

  it('pauses reconnects for clarification and resumes on queued status', () => {
    const { stream, sources, scheduled } = createHarness();
    sourceAt(sources, 0).emit('clarification.required', 'execution-a:3');
    sourceAt(sources, 0).fail();
    expect(scheduled).toHaveLength(0);

    stream.updateStatus('queued');
    expect(sources).toHaveLength(2);
    stream.dispose();
  });
});
