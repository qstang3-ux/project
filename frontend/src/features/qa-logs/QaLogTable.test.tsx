import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { QaLogSummary } from '../../api/types';
import { QaLogTable } from './QaLogTable';

const item: QaLogSummary = {
  executionId: '11111111-1111-4111-8111-111111111111', userId: 'demo-user', requestId: 'req-1', question: '查询各经营单元收入', status: 'completed',
  modelName: 'deepseek-flash', rowCount: 21, durationMs: 2300, errorCode: null, createdAt: '2026-09-17T00:00:00Z',
};

describe('QaLogTable', () => {
  it('shows the auditable business summary and opens details', () => {
    const onView = vi.fn();
    const { container } = render(<QaLogTable items={[item]} loading={false} page={1} pageSize={20} total={1} onPageChange={vi.fn()} onView={onView} />);
    expect(screen.getByText('查询各经营单元收入')).toBeInTheDocument();
    expect(screen.getByText('deepseek-flash')).toBeInTheDocument();
    expect(screen.getByText('2.3s')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /详情/ }));
    expect(onView).toHaveBeenCalledWith(item.executionId);
    const pagination = container.querySelector<HTMLElement>('.qa-log-pagination');
    expect(pagination).toBeInTheDocument();
    expect(container.querySelector<HTMLElement>('.ant-table-body')).not.toContainElement(pagination);
  }, 10_000);
});
