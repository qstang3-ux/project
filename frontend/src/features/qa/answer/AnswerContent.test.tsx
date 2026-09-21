import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ExecutionDetail } from '../../../api/types';
import { AnswerContent } from './AnswerContent';

const execution = (status: ExecutionDetail['status'], answer: string | null = null): ExecutionDetail => ({
  id: 'execution-loading', requestId: 'request-loading', sessionId: 'session-loading', userMessageId: 'user-loading', assistantMessageId: null,
  question: '测试问题', intent: 'chat', normalizedQuestion: '测试问题', missingSlots: [], clarificationRound: 0, clarification: null,
  dataSourceIds: ['source-1'], status, sqlValidationStatus: 'not_started', steps: [], selectedObjects: [], sql: null, result: null,
  answer, chart: null, followUpQuestions: [], modelName: 'deepseek-flash', currentVersionNo: 1, durationMs: null, error: null,
  tokenUsage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
  createdAt: '2026-09-17T00:00:00Z', completedAt: null,
});

describe('AnswerContent', () => {
  it('shows a clear answer loading state while an execution is running', () => {
    render(<AnswerContent execution={execution('running')} />);
    expect(screen.getByRole('status')).toHaveTextContent('正在生成回答');
  });

  it('does not show answer loading for clarification waits', () => {
    render(<AnswerContent execution={execution('awaiting_input')} />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('keeps chat answers concise without execution steps or answer evidence', () => {
    const completed = execution('completed', '你好，有什么可以帮你？');
    completed.steps = [{ type: 'intent_classification', status: 'completed', summary: '已识别为闲聊', durationMs: 12 }];
    render(<AnswerContent execution={completed} />);

    expect(screen.getByText('你好，有什么可以帮你？')).toBeInTheDocument();
    expect(screen.queryByText('执行过程')).not.toBeInTheDocument();
    expect(screen.queryByText('为什么是这个答案')).not.toBeInTheDocument();
  });

  it('retains execution steps and evidence for data queries', () => {
    const completed = execution('completed', '查询完成');
    completed.intent = 'data_query';
    completed.steps = [{ type: 'intent_classification', status: 'completed', summary: '已识别为数据查询', durationMs: 12 }];
    render(<AnswerContent execution={completed} />);

    expect(screen.getByText('执行过程')).toBeInTheDocument();
    expect(screen.getByText('为什么是这个答案')).toBeInTheDocument();
  });

  it('renders the analysis conclusion after result content', () => {
    const completed = execution('completed', '最终结论');
    completed.result = { columns: [{ key: 'name', label: '名称', dataType: 'string' }], rows: [{ name: '北京' }], rowCount: 1, truncated: false };
    const { container } = render(<AnswerContent execution={completed} />);
    const table = container.querySelector('.ant-table-wrapper');
    const conclusion = screen.getByText('最终结论').closest('.answer-summary');
    expect(table).not.toBeNull();
    expect(conclusion).not.toBeNull();
    expect(screen.queryByText('分析结论')).not.toBeInTheDocument();
    if (!table || !conclusion) throw new Error('Result table or conclusion was not rendered');
    expect(table.compareDocumentPosition(conclusion) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
