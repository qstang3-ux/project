import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QuestionComposer } from './QuestionComposer';
import type {
  BrowserSpeechRecognition,
  BrowserSpeechRecognitionErrorEvent,
  BrowserSpeechRecognitionEvent,
  BrowserSpeechRecognitionResult,
  BrowserSpeechRecognitionResultList,
} from '../speech/browserSpeech';

vi.mock('../quick-questions/QuickQuestions', () => ({
  QuickQuestions: () => <button type="button">快捷提问</button>,
}));

const recognitionInstances = new Set<BrowserSpeechRecognition>();

class SpeechRecognitionStub implements BrowserSpeechRecognition {
  lang = '';
  continuous = false;
  interimResults = false;
  maxAlternatives = 1;
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null = null;
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null = null;

  constructor() {
    recognitionInstances.add(this);
  }

  start() { this.onstart?.(); }
  stop() { this.onend?.(); }
  abort() { this.onend?.(); }
}

describe('QuestionComposer', () => {
  afterEach(() => {
    recognitionInstances.clear();
    Object.defineProperty(window, 'SpeechRecognition', { configurable: true, value: undefined });
  });

  it('preserves Shift+Enter and locks rapid duplicate submissions', () => {
    const onSubmit = vi.fn();
    const onChange = vi.fn();
    render(
      <QuestionComposer
        value="查询目标"
        onChange={onChange}
        onSubmit={onSubmit}
        onStop={vi.fn()}
        running={false}
        sources={[]}
        selectedSourceIds={['source-1']}
        maxSelection={8}
        sourcesLoading={false}
        sourcesError={false}
        onSourcesChange={vi.fn()}
        onQuickQuestionSelect={vi.fn()}
      />,
    );

    const input = screen.getByRole('textbox', { name: '问题输入' });
    expect(screen.getByRole('button', { name: '选择数据源，当前已选 1 个' })).toHaveTextContent('1 个数据源');
    const sendButton = screen.getByRole('button', { name: '发送问题' });
    expect(sendButton).toHaveClass('send-question-button');
    expect(sendButton).toHaveTextContent('');
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.keyDown(input, { key: 'Enter' });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('puts final browser speech recognition text into the editor without submitting', () => {
    Object.defineProperty(window, 'SpeechRecognition', { configurable: true, value: SpeechRecognitionStub });
    const onChange = vi.fn();
    const onSubmit = vi.fn();
    render(
      <QuestionComposer
        value="查询2026年收入"
        onChange={onChange}
        onSubmit={onSubmit}
        onStop={vi.fn()}
        running={false}
        sources={[]}
        selectedSourceIds={['source-1']}
        maxSelection={8}
        sourcesLoading={false}
        sourcesError={false}
        onSourcesChange={vi.fn()}
        onQuickQuestionSelect={vi.fn()}
        speechEnabled
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '开始语音输入' }));
    const listeningButton = screen.getByRole('button', { name: '停止语音输入' });
    expect(listeningButton).toBeEnabled();
    expect(listeningButton).toHaveAttribute('aria-pressed', 'true');
    expect(listeningButton).toHaveClass('is-listening');

    const result: BrowserSpeechRecognitionResult = {
      0: { transcript: '按月份展示' },
      length: 1,
      isFinal: true,
    };
    const results: BrowserSpeechRecognitionResultList = { 0: result, length: 1 };
    const recognitionEvent: BrowserSpeechRecognitionEvent = Object.assign(new Event('result'), {
      resultIndex: 0,
      results,
    });
    act(() => {
      const recognitionInstance = recognitionInstances.values().next().value;
      recognitionInstance?.onresult?.(recognitionEvent);
      recognitionInstance?.onend?.();
    });

    expect(onChange).toHaveBeenCalledWith('查询2026年收入\n按月份展示');
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '开始语音输入' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('uses a compact animated stop control while an answer is running', () => {
    const onStop = vi.fn();
    const { container } = render(
      <QuestionComposer
        value="查询目标"
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onStop={onStop}
        running
        sources={[]}
        selectedSourceIds={['source-1']}
        maxSelection={8}
        sourcesLoading={false}
        sourcesError={false}
        onSourcesChange={vi.fn()}
        onQuickQuestionSelect={vi.fn()}
      />,
    );

    const stopButton = screen.getByRole('button', { name: '停止当前问数' });
    expect(stopButton).toHaveClass('send-running-button');
    expect(stopButton).toHaveTextContent('');
    expect(container.querySelector('.send-running-indicator')).not.toBeNull();
    fireEvent.click(stopButton);
    expect(onStop).toHaveBeenCalledTimes(1);
  });
});
