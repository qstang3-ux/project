import { describe, expect, it } from 'vitest';
import type { ResultColumn } from '../../../api/types';
import { getVisibleResultColumns, isTechnicalResultColumn } from './resultColumnVisibility';

const column = (key: string, label: string): ResultColumn => ({ key, label, dataType: 'string', unit: null });

describe('result column visibility', () => {
  it('hides internal identifiers and generated row indexes', () => {
    expect(isTechnicalResultColumn(column('id', 'ID'))).toBe(true);
    expect(isTechnicalResultColumn(column('business_unit_id', '经营单元ID'))).toBe(true);
    expect(isTechnicalResultColumn(column('executionId', '执行标识'))).toBe(true);
    expect(isTechnicalResultColumn(column('row_number', '行号'))).toBe(true);
  });

  it('keeps meaningful business dimensions and metrics', () => {
    const visible = getVisibleResultColumns([
      column('project_code', '项目编码'),
      column('business_unit_name', '经营单元'),
      column('revenue', '收入额'),
      column('record_uuid', 'UUID'),
    ]);

    expect(visible.map((item) => item.key)).toEqual(['project_code', 'business_unit_name', 'revenue']);
  });
});
