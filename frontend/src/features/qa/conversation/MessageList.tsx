import { Empty, Skeleton } from 'antd';
import type { ExecutionDetail, Message } from '../../../api/types';
import { AssistantMessage } from '../answer/AssistantMessage';
import { PlainAssistantMessage } from './PlainAssistantMessage';
import { UserMessage } from './UserMessage';
import { getLastUserMessageByExecution } from './messageExecutionAnchors';

interface MessageListProps {
  messages: Message[];
  loading: boolean;
  activeExecution?: ExecutionDetail;
  activeExecutionId?: string;
  onFollowUp: (question: string) => void;
  onResubmit?: (message: Message, question: string) => void;
  resubmitting?: boolean;
  interactionDisabled?: boolean;
  onRegenerate?: (messageId: string) => void;
  regenerating?: boolean;
  speechEnabled?: boolean;
}

export function MessageList({ messages, loading, activeExecution, activeExecutionId, onFollowUp, onResubmit, resubmitting = false, interactionDisabled = false, onRegenerate, regenerating = false, speechEnabled = false }: MessageListProps) {
  if (loading) return <div className="message-loading"><Skeleton active paragraph={{ rows: 10 }} /></div>;
  if (!messages.length && !activeExecutionId) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="这个会话还没有消息" />;
  const renderedExecutionIds = new Set<string>();
  const userAnchors = getLastUserMessageByExecution(messages);
  return <div className="message-list">{messages.map((item) => {
    if (item.role === 'user') {
      const executionId = item.executionId;
      const executionCard = executionId && userAnchors.get(executionId) === item.id && !renderedExecutionIds.has(executionId)
        ? <AssistantMessage executionId={executionId} onFollowUp={onFollowUp} onRegenerate={onRegenerate} regenerating={regenerating} speechEnabled={speechEnabled} animateAnswer={activeExecutionId === executionId} />
        : null;
      if (executionCard && executionId) renderedExecutionIds.add(executionId);
      return <div key={item.id} className="message-turn"><UserMessage message={item} disabled={interactionDisabled} submitting={resubmitting} onResubmit={onResubmit} />{executionCard}</div>;
    }
    if (!item.executionId) {
      if (activeExecution?.assistantMessageId === item.id && activeExecutionId && !renderedExecutionIds.has(activeExecutionId)) {
        renderedExecutionIds.add(activeExecutionId);
        return <AssistantMessage key={item.id} executionId={activeExecutionId} preview={activeExecution} onFollowUp={onFollowUp} onRegenerate={onRegenerate} regenerating={regenerating} speechEnabled={speechEnabled} animateAnswer />;
      }
      if (activeExecution?.assistantMessageId === item.id) return null;
      return <PlainAssistantMessage key={item.id} message={item} speechEnabled={speechEnabled} />;
    }
    if (renderedExecutionIds.has(item.executionId) || userAnchors.has(item.executionId)) return null;
    renderedExecutionIds.add(item.executionId);
    return <AssistantMessage key={item.id} executionId={item.executionId} onFollowUp={onFollowUp} onRegenerate={onRegenerate} regenerating={regenerating} speechEnabled={speechEnabled} animateAnswer={activeExecutionId === item.executionId} />;
  })}
  {activeExecutionId && !renderedExecutionIds.has(activeExecutionId) ? <AssistantMessage executionId={activeExecutionId} preview={activeExecution} onFollowUp={onFollowUp} onRegenerate={onRegenerate} regenerating={regenerating} speechEnabled={speechEnabled} animateAnswer /> : null}
  </div>;
}
