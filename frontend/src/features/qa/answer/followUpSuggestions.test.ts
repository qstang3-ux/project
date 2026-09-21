import { describe, expect, it } from 'vitest';
import { contextualFollowUps } from './followUpSuggestions';

describe('contextualFollowUps', () => {
  it('prefers backend suggestions and removes duplicates', () => {
    expect(contextualFollowUps(['查看趋势', '查看趋势', '解释口径'], null)).toEqual(['查看趋势', '解释口径']);
  });

  it('offers chart-aware fallback suggestions', () => {
    expect(contextualFollowUps([], { type: 'line', title: null, xField: 'month', yFields: ['revenue'] })).toContain('对比上一周期的变化');
  });
});
