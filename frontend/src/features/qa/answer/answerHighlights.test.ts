import { describe, expect, it } from 'vitest';
import { buildAnswerHighlights } from './buildAnswerHighlights';

describe('buildAnswerHighlights', () => {
  it('uses existing result values without deriving new business numbers', () => {
    const highlights = buildAnswerHighlights({
      columns: [
        { key: 'business_unit_name', label: '经营单元', dataType: 'string', unit: null },
        { key: 'target_amount', label: '商业目标', dataType: 'decimal', unit: '元' },
      ],
      rows: [{ business_unit_name: '北京代表处', target_amount: 79500000 }],
      rowCount: 5,
      truncated: false,
    });

    expect(highlights).toEqual([
      { label: '首条结果', value: '北京代表处' },
      { label: '商业目标', value: '79,500,000' },
      { label: '结果规模', value: '1 / 5 行' },
    ]);
  });
});
