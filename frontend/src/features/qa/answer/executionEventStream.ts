import type { ExecutionEvent, ExecutionEventType, ExecutionStatus } from '../../../api/types';
import type { ExecutionEventCursorCheck } from '../../../api/client';
import type { EventStreamSource } from '../../../api/fetchEventSource';

export const executionEventTypes: ExecutionEventType[] = [
  'execution.started',
  'clarification.required',
  'schema.selected',
  'sql.generated',
  'sql.validated',
  'query.completed',
  'answer.completed',
  'execution.completed',
  'execution.failed',
  'execution.cancelled',
];

const terminalStatuses = new Set<ExecutionStatus>(['completed', 'failed', 'cancelled', 'rejected']);
const terminalEvents = new Set<ExecutionEventType>(['execution.completed', 'execution.failed', 'execution.cancelled']);

type Timer = ReturnType<typeof setTimeout>;

interface ExecutionEventStreamOptions {
  executionId: string;
  initialStatus?: ExecutionStatus;
  refresh: () => void;
  createEventSource: (url: string) => EventStreamSource;
  eventsUrl: (executionId: string, lastEventId?: string) => string;
  checkCursor: (executionId: string, lastEventId: string) => Promise<ExecutionEventCursorCheck>;
  schedule?: (callback: () => void, delay: number) => Timer;
  cancelSchedule?: (timer: Timer) => void;
  reconnectDelays?: readonly number[];
}

export class ExecutionEventStream {
  private readonly options: Required<Pick<ExecutionEventStreamOptions, 'schedule' | 'cancelSchedule' | 'reconnectDelays'>> & ExecutionEventStreamOptions;
  private source?: EventStreamSource;
  private reconnectTimer?: Timer;
  private reconnectAttempt = 0;
  private status?: ExecutionStatus;
  private waitingForClarification = false;
  private disposed = false;
  private generation = 0;
  private lastEventId?: string;
  private readonly seenEventIds = new Set<string>();
  private readonly listeners = new Map<ExecutionEventType, EventListener>();

  constructor(options: ExecutionEventStreamOptions) {
    this.options = {
      ...options,
      schedule: options.schedule ?? ((callback, delay) => setTimeout(callback, delay)),
      cancelSchedule: options.cancelSchedule ?? ((timer) => clearTimeout(timer)),
      reconnectDelays: options.reconnectDelays ?? [300, 700, 1500],
    };
    this.status = options.initialStatus;
    if (this.status === 'queued' || this.status === 'running') this.connect(false);
  }

  updateStatus(status: ExecutionStatus | undefined) {
    const wasWaiting = this.status === 'awaiting_input' || this.waitingForClarification;
    this.status = status;
    if (this.isTerminal()) {
      this.generation += 1;
      this.stopConnection();
      return;
    }
    if (status === 'awaiting_input') {
      this.generation += 1;
      this.waitingForClarification = true;
      this.clearReconnectTimer();
      return;
    }
    if (status === 'queued' || status === 'running') {
      this.waitingForClarification = false;
      if (wasWaiting) this.reconnectAttempt = 0;
      if (!this.source) this.connect(Boolean(this.lastEventId));
    }
  }

  dispose() {
    this.disposed = true;
    this.generation += 1;
    this.clearReconnectTimer();
    this.stopConnection();
    this.lastEventId = undefined;
    this.seenEventIds.clear();
  }

  private connect(useCursor: boolean) {
    if (this.disposed || this.source || this.isTerminal() || this.waitingForClarification) return;
    const source = this.options.createEventSource(this.options.eventsUrl(this.options.executionId, useCursor ? this.lastEventId : undefined));
    this.source = source;
    const onMessage = (event: Event) => {
      const message = event as MessageEvent<string>;
      try {
        const payload = JSON.parse(message.data) as ExecutionEvent;
        this.handleEvent(payload.type, message, payload.id);
      } catch {
        this.handleEvent(undefined, message);
      }
    };
    source.onmessage = onMessage;
    executionEventTypes.forEach((eventType) => {
      const listener: EventListener = (event) => {
        const message = event as MessageEvent<string>;
        let payloadId: string | undefined;
        try {
          payloadId = (JSON.parse(message.data) as ExecutionEvent).id;
        } catch {
          payloadId = undefined;
        }
        this.handleEvent(eventType, message, payloadId);
      };
      this.listeners.set(eventType, listener);
      source.addEventListener(eventType, listener);
    });
    source.onerror = () => this.handleDisconnect(source);
  }

  private handleEvent(eventType: ExecutionEventType | undefined, event: MessageEvent<string>, payloadId?: string) {
    if (this.disposed) return;
    const eventId = event.lastEventId || payloadId;
    if (eventId && this.seenEventIds.has(eventId)) return;
    if (eventId) {
      this.seenEventIds.add(eventId);
      this.lastEventId = eventId;
    }
    this.reconnectAttempt = 0;
    this.clearReconnectTimer();
    this.options.refresh();
    if (eventType === 'clarification.required') {
      this.waitingForClarification = true;
      return;
    }
    if (eventType && terminalEvents.has(eventType)) this.stopConnection();
  }

  private handleDisconnect(source: EventStreamSource) {
    if (this.source !== source) return;
    this.stopConnection();
    if (this.disposed || this.isTerminal() || this.waitingForClarification) return;
    this.scheduleReconnect();
  }

  private scheduleReconnect() {
    if (this.disposed || this.reconnectTimer || this.reconnectAttempt >= this.options.reconnectDelays.length) return;
    const delay = this.options.reconnectDelays[this.reconnectAttempt];
    if (delay === undefined) return;
    this.reconnectAttempt += 1;
    this.reconnectTimer = this.options.schedule(() => {
      this.reconnectTimer = undefined;
      void this.reconnect();
    }, delay);
  }

  private async reconnect() {
    if (this.disposed || this.isTerminal() || this.waitingForClarification) return;
    if (!this.lastEventId) {
      this.connect(false);
      return;
    }
    const generation = this.generation;
    const cursorCheck = await this.options.checkCursor(this.options.executionId, this.lastEventId);
    if (generation !== this.generation) return;
    if (cursorCheck === 'reset') {
      this.lastEventId = undefined;
      this.seenEventIds.clear();
      this.reconnectAttempt = 0;
      this.options.refresh();
      this.connect(false);
      return;
    }
    if (cursorCheck === 'valid') {
      this.connect(true);
      return;
    }
    this.scheduleReconnect();
  }

  private stopConnection() {
    const source = this.source;
    this.source = undefined;
    if (!source) return;
    executionEventTypes.forEach((eventType) => {
      const listener = this.listeners.get(eventType);
      if (listener) source.removeEventListener(eventType, listener);
    });
    this.listeners.clear();
    source.onmessage = null;
    source.onerror = null;
    source.close();
  }

  private clearReconnectTimer() {
    if (!this.reconnectTimer) return;
    this.options.cancelSchedule(this.reconnectTimer);
    this.reconnectTimer = undefined;
  }

  private isTerminal() {
    return this.status ? terminalStatuses.has(this.status) : false;
  }
}
