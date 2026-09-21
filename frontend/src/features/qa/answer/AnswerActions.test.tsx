import { fireEvent, render, screen } from '@testing-library/react';
import { App } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ExecutionDetail } from '../../../api/types';
import { AnswerActions } from './AnswerActions';

class SpeechSynthesisUtteranceStub {
  lang = '';
  rate = 1;
  voice: SpeechSynthesisVoice | null = null;
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(readonly text: string) {}
}

const execution: ExecutionDetail = {
  id: '00000000-0000-0000-0000-000000000001',
  requestId: 'request-1',
  sessionId: '00000000-0000-0000-0000-000000000002',
  userMessageId: '00000000-0000-0000-0000-000000000003',
  assistantMessageId: '00000000-0000-0000-0000-000000000004',
  question: '查询经营数据',
  missingSlots: [],
  clarificationRound: 0,
  dataSourceIds: ['00000000-0000-0000-0000-000000000005'],
  status: 'completed',
  sqlValidationStatus: 'passed',
  steps: [],
  result: { columns: [{ key: 'amount', label: '金额', dataType: 'decimal' }], rows: [{ amount: '100' }], rowCount: 1, truncated: false },
  answer: '这是经营分析结果。',
  chart: null,
  tokenUsage: { promptTokens: 1200, completionTokens: 345, totalTokens: 1545 },
  error: null,
  createdAt: '2026-09-17T00:00:00Z',
};

describe('AnswerActions', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders compact icon-only actions with accessible names', () => {
    Object.defineProperty(globalThis, 'SpeechSynthesisUtterance', {
      configurable: true,
      value: SpeechSynthesisUtteranceStub,
    });
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: { speak: vi.fn(), cancel: vi.fn(), getVoices: () => [] },
    });
    const onFeedback = vi.fn();
    const onVersions = vi.fn();
    const onRegenerate = vi.fn();
    const onExport = vi.fn();

    render(<App><AnswerActions execution={execution} speechEnabled onFeedback={onFeedback} onVersions={onVersions} onRegenerate={onRegenerate} onExport={onExport} /></App>);

    const copyButton = screen.getByRole('button', { name: '复制回答' });
    const speechButton = screen.getByRole('button', { name: '朗读回答' });
    const feedbackButton = screen.getByRole('button', { name: '数据有误' });
    const regenerateButton = screen.getByRole('button', { name: '重新生成回答' });
    const versionsButton = screen.getByRole('button', { name: '查看回答版本' });
    const exportButton = screen.getByRole('button', { name: '导出 CSV' });
    expect(copyButton.textContent).toBe('');
    expect(speechButton.textContent).toBe('');
    expect(feedbackButton.textContent).toBe('');
    expect(regenerateButton.textContent).toBe('');
    expect(versionsButton.textContent).toBe('');
    expect(exportButton.textContent).toBe('');
    expect(screen.getByText(/Token 1,545/)).toBeInTheDocument();

    fireEvent.click(feedbackButton);
    expect(onFeedback).toHaveBeenCalledTimes(1);
    fireEvent.click(regenerateButton);
    fireEvent.click(versionsButton);
    fireEvent.click(exportButton);
    expect(onRegenerate).toHaveBeenCalledTimes(1);
    expect(onVersions).toHaveBeenCalledTimes(1);
    expect(onExport).toHaveBeenCalledTimes(1);
  });
});
