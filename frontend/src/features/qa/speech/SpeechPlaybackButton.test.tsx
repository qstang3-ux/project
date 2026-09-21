import { act, fireEvent, render, screen } from '@testing-library/react';
import { App } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SpeechPlaybackButton } from './SpeechPlaybackButton';

class SpeechSynthesisUtteranceStub {
  lang = '';
  rate = 1;
  voice: SpeechSynthesisVoice | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;

  constructor(readonly text: string) {}
}

describe('SpeechPlaybackButton', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('starts and stops browser speech synthesis on demand', () => {
    const speak = vi.fn();
    const cancel = vi.fn();
    Object.defineProperty(globalThis, 'SpeechSynthesisUtterance', {
      configurable: true,
      value: SpeechSynthesisUtteranceStub,
    });
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: { speak, cancel, getVoices: () => [] },
    });

    render(<App><SpeechPlaybackButton text="这是经营分析结果" enabled /></App>);
    const playButton = screen.getByRole('button', { name: '朗读回答' });
    expect(playButton).toHaveAttribute('aria-pressed', 'false');
    expect(playButton).toHaveTextContent('');
    fireEvent.click(playButton);

    expect(speak).toHaveBeenCalledTimes(1);
    expect(speak.mock.calls[0]?.[0]).toMatchObject({ text: '这是经营分析结果', lang: 'zh-CN', rate: 1 });

    const stopButton = screen.getByRole('button', { name: '停止朗读' });
    expect(stopButton).toHaveAttribute('aria-pressed', 'true');
    expect(stopButton).toHaveClass('is-speaking');
    expect(stopButton).toHaveTextContent('');
    fireEvent.click(stopButton);
    expect(cancel).toHaveBeenCalledTimes(2);

    const utterance = speak.mock.calls[0]?.[0] as SpeechSynthesisUtteranceStub;
    act(() => utterance.onerror?.({ error: 'interrupted' }));
    expect(screen.queryByText('语音播放失败，请检查系统音频设置。')).not.toBeInTheDocument();
  });
});
