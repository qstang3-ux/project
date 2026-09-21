import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ClarificationPrompt } from './ClarificationPrompt';

describe('ClarificationPrompt', () => {
  it('shows missing slots and submits trimmed clarification content', () => {
    const onSubmit = vi.fn();
    render(
      <ClarificationPrompt
        clarification={{ prompt: '请补充查询年份', missingSlots: ['年份'], round: 1, maxRounds: 2 }}
        intent="clarification"
        normalizedQuestion="查询经营数据"
        missingSlots={['年份']}
        clarificationRound={1}
        submitting={false}
        cancelling={false}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText('待补充')).toBeInTheDocument();
    expect(screen.getByText('年份')).toBeInTheDocument();
    expect(screen.getByText('需要补充信息')).toBeInTheDocument();
    expect(screen.getByText('查询经营数据')).toBeInTheDocument();
    expect(screen.getByText('第 1 / 2 轮')).toBeInTheDocument();
    const submit = screen.getByRole('button', { name: '提交并继续' });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByRole('textbox', { name: '补充信息' }), { target: { value: '  2026 年  ' } });
    fireEvent.click(submit);
    expect(onSubmit).toHaveBeenCalledWith('2026 年');
  });

  it('renders untrusted prompt as text and confirms cancellation', () => {
    const onCancel = vi.fn();
    const prompt = '<img src=x onerror=alert(1)>';
    render(
      <ClarificationPrompt
        clarification={{ prompt, missingSlots: [], round: 2, maxRounds: 2 }}
        intent="clarification"
        normalizedQuestion={null}
        missingSlots={[]}
        clarificationRound={2}
        submitting={false}
        cancelling={false}
        onSubmit={vi.fn()}
        onCancel={onCancel}
      />,
    );

    expect(screen.getByText(prompt)).toBeInTheDocument();
    expect(document.querySelector('img')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: '停止' }));
    const confirm = document.querySelector<HTMLButtonElement>('.ant-popconfirm-buttons .ant-btn-primary');
    if (!confirm) throw new Error('缺少停止确认按钮');
    fireEvent.click(confirm);
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
