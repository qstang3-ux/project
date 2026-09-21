import { EyeOutlined } from '@ant-design/icons';
import { Button, Pagination, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { ExecutionStatus, QaLogSummary } from '../../api/types';
import { executionStatusColors, executionStatusLabels } from './qaLogPresentation';

export function QaLogTable(props: { items: QaLogSummary[]; loading: boolean; page: number; pageSize: number; total: number; onPageChange: (page: number, pageSize: number) => void; onView: (id: string) => void }) {
  const columns: ColumnsType<QaLogSummary> = [
    { title: '用户问题', dataIndex: 'question', ellipsis: true, render: (value: string) => <span className="qa-log-question">{value}</span> },
    { title: '用户', dataIndex: 'userId', width: 120 },
    { title: '状态', dataIndex: 'status', width: 105, render: (value: ExecutionStatus) => <Tag color={executionStatusColors[value]}>{executionStatusLabels[value]}</Tag> },
    { title: '模型', dataIndex: 'modelName', width: 150, ellipsis: true, render: (value: string | null) => value ?? '--' },
    { title: '行数', dataIndex: 'rowCount', width: 80, align: 'right', render: (value: number | null) => value ?? '--' },
    { title: '耗时', dataIndex: 'durationMs', width: 95, align: 'right', render: (value: number | null) => value === null ? '--' : `${(value / 1000).toFixed(1)}s` },
    { title: '发生时间', dataIndex: 'createdAt', width: 185, render: (value: string) => new Date(value).toLocaleString('zh-CN') },
    { title: '操作', width: 86, fixed: 'right', render: (_, record) => <Button className="table-action-button" type="text" size="small" icon={<EyeOutlined />} onClick={() => props.onView(record.executionId)}>详情</Button> },
  ];
  return (
    <div className="qa-log-table">
      <Table<QaLogSummary>
        rowKey="executionId"
        loading={props.loading}
        dataSource={props.items}
        columns={columns}
        scroll={{ x: 1050, y: 'max(180px, calc(100vh - 510px))' }}
        pagination={false}
      />
      <Pagination
        className="qa-log-pagination"
        current={props.page}
        pageSize={props.pageSize}
        total={props.total}
        showSizeChanger
        showTotal={(total) => `共 ${String(total)} 条`}
        onChange={props.onPageChange}
      />
    </div>
  );
}
