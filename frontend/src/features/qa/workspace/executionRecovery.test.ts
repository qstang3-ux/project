import { describe, expect, it } from 'vitest';
import type { Message } from '../../../api/types';
import { findActiveExecutionId } from './executionRecovery';

const message = (id: string, executionId: string, executionStatus: Message['executionStatus']): Message => ({
  id,
  sessionId: 'session-1',
  role: 'user',
  content: id,
  executionId,
  executionStatus,
  createdAt: '2026-09-16T00:00:00Z',
});

describe('findActiveExecutionId', () => {
  it('restores the latest queued, running or awaiting-input execution after refresh', () => {
    expect(findActiveExecutionId([
      message('old', 'execution-completed', 'completed'),
      message('queued', 'execution-queued', 'queued'),
      message('running', 'execution-running', 'running'),
      message('clarification', 'execution-clarification', 'awaiting_input'),
    ])).toBe('execution-clarification');
  });

  it('does not restore terminal executions', () => {
    expect(findActiveExecutionId([
      message('completed', 'execution-completed', 'completed'),
      message('failed', 'execution-failed', 'failed'),
    ])).toBeUndefined();
  });
});
