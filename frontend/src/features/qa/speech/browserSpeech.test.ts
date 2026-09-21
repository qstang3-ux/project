import { describe, expect, it } from 'vitest';
import { appendTranscript, speechRecognitionErrorMessage } from './browserSpeech';

describe('browser speech helpers', () => {
  it('appends recognized text without sending or replacing the existing question', () => {
    expect(appendTranscript('查询2026年收入', '按月份展示')).toBe('查询2026年收入\n按月份展示');
    expect(appendTranscript('', '查询目标完成率')).toBe('查询目标完成率');
  });

  it('maps permission and network failures to actionable Chinese messages', () => {
    expect(speechRecognitionErrorMessage('not-allowed')).toContain('麦克风权限');
    expect(speechRecognitionErrorMessage('network')).toContain('文字输入');
    expect(speechRecognitionErrorMessage('unknown')).toContain('语音识别失败');
  });
});
