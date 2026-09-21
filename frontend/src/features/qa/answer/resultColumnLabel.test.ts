import { describe, expect, it } from 'vitest';
import { getResultColumnLabel } from './resultColumnLabel';

describe('getResultColumnLabel', () => {
  it('localizes known raw database field names', () => {
    expect(getResultColumnLabel({ key: 'year', label: 'year', dataType: 'integer', unit: null })).toBe('年度');
    expect(getResultColumnLabel({ key: 'revenue_amount', label: 'revenue_amount', dataType: 'decimal', unit: null })).toBe('收入额');
    expect(getResultColumnLabel({ key: 'prior_year_revenue', label: 'prior_year_revenue', dataType: 'decimal', unit: null })).toBe('上年同期收入');
    expect(getResultColumnLabel({ key: 'yoy_change_amount', label: 'yoy_change_amount', dataType: 'decimal', unit: null })).toBe('同比增量');
    expect(getResultColumnLabel({ key: 'yoy_growth_rate', label: 'yoy_growth_rate', dataType: 'percent', unit: null })).toBe('同比增长率');
    expect(getResultColumnLabel({ key: 'business_unit_code', label: 'business_unit_code', dataType: 'string', unit: null })).toBe('经营单元编码');
    expect(getResultColumnLabel({ key: 'contract_no', label: 'contract_no', dataType: 'string', unit: null })).toBe('合同编号');
  });

  it('preserves an explicit backend label and safely falls back for unknown fields', () => {
    expect(getResultColumnLabel({ key: 'revenue_amount', label: '营业收入', dataType: 'decimal', unit: null })).toBe('营业收入');
    expect(getResultColumnLabel({ key: 'custom_metric', label: 'custom_metric', dataType: 'decimal', unit: null })).toBe('custom_metric');
  });
});
