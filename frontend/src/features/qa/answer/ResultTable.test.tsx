import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ResultTable } from './ResultTable';

describe('ResultTable', () => {
  it('renders known raw result fields with Chinese headers', () => {
    render(<ResultTable result={{
      columns: [
        { key: 'year', label: 'year', dataType: 'integer', unit: null },
        { key: 'revenue_amount', label: 'revenue_amount', dataType: 'decimal', unit: null },
        { key: 'prior_year_revenue', label: 'prior_year_revenue', dataType: 'decimal', unit: null },
        { key: 'yoy_change_amount', label: 'yoy_change_amount', dataType: 'decimal', unit: null },
        { key: 'yoy_growth_rate', label: 'yoy_growth_rate', dataType: 'percent', unit: null },
      ],
      rows: [{ year: 2026, revenue_amount: 100, prior_year_revenue: 80, yoy_change_amount: 20, yoy_growth_rate: 25 }],
      rowCount: 1,
      truncated: false,
    }} />);

    for (const heading of ['年度', '收入额', '上年同期收入', '同比增量', '同比增长率']) {
      expect(screen.getByRole('columnheader', { name: heading })).toBeInTheDocument();
    }
  }, 10_000);

  it('reports row focus so the chart can highlight the same data point', () => {
    const onHighlightRow = vi.fn();
    render(<ResultTable onHighlightRow={onHighlightRow} result={{
      columns: [{ key: 'name', label: '名称', dataType: 'string', unit: null }],
      rows: [{ name: '北京代表处' }],
      rowCount: 1,
      truncated: false,
    }} />);

    const row = screen.getByText('北京代表处').closest('tr');
    if (!row) throw new Error('结果行未渲染');
    fireEvent.mouseEnter(row);
    expect(onHighlightRow).toHaveBeenLastCalledWith(0);
    fireEvent.mouseLeave(row);
    expect(onHighlightRow).toHaveBeenLastCalledWith(null);
  });
});
