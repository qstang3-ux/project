import { describe, expect, it } from 'vitest';
import { buildChartOption } from './chartOption';
import { chartPngFilename } from './chartExport';
import type { ResultSet } from '../../../api/types';

const result: ResultSet = {
  columns: [{ key: 'name', label: '名称', dataType: 'string' }, { key: 'value', label: '数值', dataType: 'decimal' }],
  rows: [{ name: '北京', value: '10' }],
  rowCount: 1,
  truncated: false,
};

describe('buildChartOption', () => {
  it('builds a local bar chart config from structured fields', () => {
    const option = buildChartOption({ type: 'bar', xField: 'name', yFields: ['value'], unit: '万元' }, result);
    expect(option).not.toBeNull();
    expect(option).toMatchObject({
      xAxis: { axisLabel: { hideOverlap: true, interval: 'auto' } },
      series: [{ type: 'bar' }],
    });
  });

  it('adds horizontal zoom for crowded category axes', () => {
    const crowdedResult: ResultSet = {
      ...result,
      rows: Array.from({ length: 18 }, (_, index) => ({ name: `第 ${String(index + 1)} 个较长分类名称`, value: String(index) })),
      rowCount: 18,
    };
    const option = buildChartOption({ type: 'line', xField: 'name', yFields: ['value'] }, crowdedResult);

    expect(option).toMatchObject({
      grid: { bottom: 104 },
      xAxis: { axisLabel: { rotate: 28, overflow: 'truncate' } },
      dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    });
  });

  it('rejects incomplete chart specs so the table can remain as fallback', () => {
    expect(buildChartOption({ type: 'bar', yFields: ['value'] }, result)).toBeNull();
    expect(buildChartOption({ type: 'pie', nameField: 'name' }, result)).toBeNull();
  });

  it('builds a filesystem-safe PNG filename', () => {
    expect(chartPngFilename('收入/趋势:2026')).toBe('收入-趋势-2026.png');
    expect(chartPngFilename()).toBe('经营分析图表.png');
  });

  it('uses the shared Chinese column label in chart legends', () => {
    const option = buildChartOption({ type: 'bar', xField: 'name', yFields: ['commercial_target_amount'] }, {
      columns: [{ key: 'name', label: '名称', dataType: 'string' }, { key: 'commercial_target_amount', label: 'commercial_target_amount', dataType: 'decimal' }],
      rows: [{ name: '北京代表处', commercial_target_amount: 79500000 }],
      rowCount: 1,
      truncated: false,
    });
    expect(option).toMatchObject({ series: [{ name: '商业目标' }] });
  });
});
