import { Table } from 'antd';
import type { FeedbackSummary } from '../../api/types';
import { createFeedbackColumns } from './feedbackColumns';

interface FeedbackTableProps {
  items: FeedbackSummary[];
  loading: boolean;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number, pageSize: number) => void;
  onView: (id: string) => void;
}

export function FeedbackTable(props: FeedbackTableProps) {
  return (
    <Table<FeedbackSummary>
      rowKey="id"
      loading={props.loading}
      dataSource={props.items}
      scroll={{ x: 720 }}
      pagination={{ current: props.page, pageSize: props.pageSize, total: props.total, showSizeChanger: true, onChange: props.onPageChange }}
      columns={createFeedbackColumns(props.onView)}
    />
  );
}
