import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ClarificationPrompt } from './ClarificationPrompt';

describe('ClarificationPrompt', () => {
  it('shows missing slots without rendering a second input', () => {
    render(
      <ClarificationPrompt
        clarification={{ prompt: '请补充查询年份', missingSlots: ['年份'], round: 1, maxRounds: 2 }}
        intent="clarification"
        normalizedQuestion="查询经营数据"
        missingSlots={['年份']}
        clarificationRound={1}
      />,
    );

    expect(screen.getByText('建议补充')).toBeInTheDocument();
    expect(screen.getByText('分析年份')).toBeInTheDocument();
    expect(screen.getByText('需要补充信息')).toBeInTheDocument();
    expect(screen.getByText('查询经营数据')).toBeInTheDocument();
    expect(screen.getByText('第 1 / 2 轮')).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '提交并继续' })).not.toBeInTheDocument();
  });

  it('renders untrusted prompt as text', () => {
    const prompt = '<img src=x onerror=alert(1)>';
    render(
      <ClarificationPrompt
        clarification={{ prompt, missingSlots: [], round: 2, maxRounds: 2 }}
        intent="clarification"
        normalizedQuestion={null}
        missingSlots={[]}
        clarificationRound={2}
      />,
    );

    expect(screen.getByText(prompt)).toBeInTheDocument();
    expect(document.querySelector('img')).toBeNull();
  });
});
