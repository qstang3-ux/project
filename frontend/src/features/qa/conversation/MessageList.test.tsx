import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ExecutionDetail } from '../../../api/types';
import { MessageList } from './MessageList';

vi.mock('../answer/AssistantMessage', () => ({
  AssistantMessage: ({ executionId }: { executionId: string }) => <div data-testid={`execution-${executionId}`} />,
}));

vi.mock('../quick-questions/FavoriteQuestionButton', () => ({
  FavoriteQuestionButton: () => null,
}));

const activeExecution: ExecutionDetail = {
  id: 'e1',
  requestId: 'r1',
  sessionId: 's1',
  userMessageId: 'u1',
  assistantMessageId: 'a-current',
  question: '经营数据如何？',
  missingSlots: [],
  clarificationRound: 0,
  dataSourceIds: ['source-1'],
  status: 'completed',
  sqlValidationStatus: 'passed',
  steps: [],
  result: null,
  chart: null,
  tokenUsage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
  error: null,
  answer: '相同回答',
  createdAt: '2026-09-16T00:00:00Z',
};

describe('MessageList', () => {
  it('renders user-provided markup as escaped text', () => {
    const payload = '<img src=x onerror=alert(1)><script>window.hacked=true</script>';
    render(<MessageList loading={false} messages={[{ id: '1', sessionId: 's1', role: 'user', content: payload, createdAt: '2026-09-16T00:00:00Z' }]} onFollowUp={vi.fn()} />);
    expect(screen.getByText(payload)).toBeInTheDocument();
    expect(document.querySelector('script')).toBeNull();
    expect(document.querySelector('img')).toBeNull();
  });

  it('restores an execution from a user message and renders it only once', () => {
    render(<MessageList loading={false} messages={[
      { id: 'u1', sessionId: 's1', role: 'user', content: '危险 SQL', executionId: 'e1', createdAt: '2026-09-16T00:00:00Z' },
      { id: 'a1', sessionId: 's1', role: 'assistant', content: '已拒绝', executionId: 'e1', createdAt: '2026-09-16T00:00:01Z' },
    ]} onFollowUp={vi.fn()} />);

    expect(screen.getAllByTestId('execution-e1')).toHaveLength(1);
  });

  it('anchors one execution card after the latest clarification user message', () => {
    render(<MessageList loading={false} messages={[
      { id: 'u1', sessionId: 's1', role: 'user', content: '达成情况', executionId: 'e1', executionStatus: 'awaiting_input', createdAt: '2026-09-16T00:00:00Z' },
      { id: 'u2', sessionId: 's1', role: 'user', content: '查询2026年各经营单元商业目标完成率', executionId: 'e1', executionStatus: 'completed', createdAt: '2026-09-16T00:00:01Z' },
      { id: 'a1', sessionId: 's1', role: 'assistant', content: '已完成', executionId: 'e1', executionStatus: 'completed', createdAt: '2026-09-16T00:00:02Z' },
    ]} onFollowUp={vi.fn()} />);

    const executionCard = screen.getByTestId('execution-e1');
    expect(screen.getAllByTestId('execution-e1')).toHaveLength(1);
    expect(screen.getByText('查询2026年各经营单元商业目标完成率').closest('.message-turn')).toContainElement(executionCard);
  });

  it('associates unlinked assistant messages by message ID instead of answer content', () => {
    render(<MessageList loading={false} activeExecution={activeExecution} activeExecutionId="e1" messages={[
      { id: 'a-history', sessionId: 's1', role: 'assistant', content: '相同回答', createdAt: '2026-09-16T00:00:00Z' },
      { id: 'a-current', sessionId: 's1', role: 'assistant', content: '相同回答', createdAt: '2026-09-16T00:00:01Z' },
    ]} onFollowUp={vi.fn()} />);

    expect(screen.getByText('历史回答')).toBeInTheDocument();
    expect(screen.getAllByText('相同回答')).toHaveLength(1);
    expect(screen.getByTestId('execution-e1')).toBeInTheDocument();
  });
});
