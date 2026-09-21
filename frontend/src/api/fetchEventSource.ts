export interface EventStreamSource {
  onmessage: ((event: MessageEvent<string>) => void) | null;
  onerror: (() => void) | null;
  addEventListener(type: string, listener: EventListener): void;
  removeEventListener(type: string, listener: EventListener): void;
  close(): void;
}

interface ParsedEvent {
  type: string;
  data: string;
  id: string;
}

export function createFetchEventSource(url: string): EventStreamSource {
  return new FetchEventSource(url);
}

export function parseEventBlock(block: string): ParsedEvent | undefined {
  let type = 'message';
  let id = '';
  const data: string[] = [];

  block.split(/\r\n|\r|\n/).forEach((line) => {
    if (!line || line.startsWith(':')) return;
    const separator = line.indexOf(':');
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? '' : line.slice(separator + 1);
    if (value.startsWith(' ')) value = value.slice(1);
    if (field === 'event') type = value || 'message';
    if (field === 'data') data.push(value);
    if (field === 'id' && !value.includes('\0')) id = value;
  });

  if (data.length === 0) return undefined;
  return { type, data: data.join('\n'), id };
}

class FetchEventSource implements EventStreamSource {
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  private readonly abortController = new AbortController();
  private readonly listeners = new Map<string, Set<EventListener>>();
  private closed = false;

  constructor(url: string) {
    void this.read(url);
  }

  addEventListener(type: string, listener: EventListener) {
    const entries = this.listeners.get(type) ?? new Set<EventListener>();
    entries.add(listener);
    this.listeners.set(type, entries);
  }

  removeEventListener(type: string, listener: EventListener) {
    const entries = this.listeners.get(type);
    entries?.delete(listener);
    if (entries?.size === 0) this.listeners.delete(type);
  }

  close() {
    if (this.closed) return;
    this.closed = true;
    this.listeners.clear();
    this.onmessage = null;
    this.onerror = null;
    this.abortController.abort();
  }

  private async read(url: string) {
    try {
      const response = await fetch(url, {
        headers: { Accept: 'text/event-stream' },
        signal: this.abortController.signal,
      });
      if (!response.ok || !response.body) throw new Error(`SSE request failed with status ${String(response.status)}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      try {
        while (!this.closed) {
          const chunk = await reader.read();
          if (chunk.done) break;
          buffer += decoder.decode(chunk.value, { stream: true });
          buffer = this.dispatchCompleteBlocks(buffer);
        }
        buffer += decoder.decode();
        this.dispatchCompleteBlocks(buffer);
      } finally {
        reader.releaseLock();
      }
      if (!this.closed) this.onerror?.();
    } catch (error) {
      if (!this.closed && !(error instanceof DOMException && error.name === 'AbortError')) this.onerror?.();
    }
  }

  private dispatchCompleteBlocks(buffer: string) {
    let remaining = buffer;
    let separator = findEventSeparator(remaining);
    while (separator) {
      const block = remaining.slice(0, separator.index);
      remaining = remaining.slice(separator.index + separator.length);
      const parsed = parseEventBlock(block);
      if (parsed) this.dispatch(parsed);
      separator = findEventSeparator(remaining);
    }
    return remaining;
  }

  private dispatch(parsed: ParsedEvent) {
    if (this.closed) return;
    const event = new MessageEvent<string>(parsed.type, { data: parsed.data, lastEventId: parsed.id });
    if (parsed.type === 'message') this.onmessage?.(event);
    this.listeners.get(parsed.type)?.forEach((listener) => listener(event));
  }
}

function findEventSeparator(value: string): { index: number; length: number } | undefined {
  const match = /\r\n\r\n|\n\n|\r\r/.exec(value);
  return match?.index === undefined ? undefined : { index: match.index, length: match[0].length };
}
