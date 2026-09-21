import type { Message } from '../../../api/types';

export function findActiveExecutionId(messages: Message[]): string | undefined {
  return [...messages].reverse().find((message) => (
    message.executionId && (
      message.executionStatus === 'queued' ||
      message.executionStatus === 'running' ||
      message.executionStatus === 'awaiting_input'
    )
  ))?.executionId ?? undefined;
}
