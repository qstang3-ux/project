import type { Message } from '../../../api/types';

export function getLastUserMessageByExecution(messages: Message[]): Map<string, string> {
  const anchors = new Map<string, string>();
  messages.forEach((message) => {
    if (message.role === 'user' && message.executionId) anchors.set(message.executionId, message.id);
  });
  return anchors;
}
