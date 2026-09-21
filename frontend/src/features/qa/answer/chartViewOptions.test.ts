import { describe, expect, it } from 'vitest';
import { buildChartViewOptions } from './chartViewOptions';

const result = {
  columns: [
    { key: 'business_unit_name', label: '经营单元', dataType: 'string' as const, unit: null },
    { key: 'target_amount', label: '商业目标', dataType: 'decimal' as const, unit: '元' },
  ],
  rows: [{ business_unit_name: '北京代表处', target_amount: 79500000 }],
  rowCount: 1,
  truncated: false,
};

describe('buildChartViewOptions', () => {
  it('adapts a bar chart to line and pie without changing the result data', () => {
    const options = buildChartViewOptions({ type: 'bar', xField: 'business_unit_name', yFields: ['target_amount'] }, result);
    expect(options.every((option) => option.enabled)).toBe(true);
    expect(options.find((option) => option.type === 'pie')?.chart).toMatchObject({ nameField: 'business_unit_name', valueField: 'target_amount' });
  });

  it('disables pie charts with too many categories', () => {
    const largeResult = { ...result, rows: Array.from({ length: 13 }, (_, index) => ({ business_unit_name: `单元${String(index + 1)}`, target_amount: index })) };
    const pie = buildChartViewOptions({ type: 'bar', xField: 'business_unit_name', yFields: ['target_amount'] }, largeResult).find((option) => option.type === 'pie');
    expect(pie).toMatchObject({ enabled: false, reason: '分类超过 12 项，不适合饼图' });
  });
});
