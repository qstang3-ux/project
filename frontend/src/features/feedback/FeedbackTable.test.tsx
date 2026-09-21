import { describe, expect, it, vi } from 'vitest';
import { createFeedbackColumns } from './feedbackColumns';

describe('FeedbackTable', () => {
  it('shows business fields without exposing technical identifiers', () => {
    const columns = createFeedbackColumns(vi.fn());
    const titles = columns.map((column) => column.title);

    expect(titles).toEqual(['问题摘要', '原因', '状态', '提交时间', '操作']);
  });
});
