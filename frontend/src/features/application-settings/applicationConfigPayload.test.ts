import { describe, expect, it } from 'vitest';
import type { ApplicationConfig } from '../../api/types';
import { buildApplicationConfigUpdate } from './applicationConfigPayload';

const current: ApplicationConfig = {
  greetingEnabled: true,
  greetingText: '欢迎使用',
  recommendedQuestions: ['收入趋势'],
  followUpEnabled: true,
  frequentQuestionsEnabled: true,
  frequentQuestionThreshold: 3,
  modelQaEnabled: true,
  ttsEnabled: false,
  sttEnabled: false,
  version: 7,
  updatedAt: '2026-09-18T10:00:00Z',
};

describe('buildApplicationConfigUpdate', () => {
  it('keeps modal-only fields when a visible switch is changed', () => {
    const payload = buildApplicationConfigUpdate(current, { ttsEnabled: true, version: 7 });

    expect(payload).toEqual({
      greetingEnabled: true,
      greetingText: '欢迎使用',
      recommendedQuestions: ['收入趋势'],
      followUpEnabled: true,
      frequentQuestionsEnabled: true,
      frequentQuestionThreshold: 3,
      modelQaEnabled: true,
      ttsEnabled: true,
      sttEnabled: false,
      version: 7,
    });
    expect(payload).not.toHaveProperty('updatedAt');
  });

  it('preserves explicit false values', () => {
    expect(buildApplicationConfigUpdate(current, { greetingEnabled: false }).greetingEnabled).toBe(false);
  });
});
