import { EyeOutlined } from '@ant-design/icons';
import { Button, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { FeedbackReason, FeedbackStatus, FeedbackSummary } from '../../api/types';
import { reasonLabels, statusColors, statusLabels } from './feedbackPresentation';

export function createFeedbackColumns(onView: (id: string) => void): ColumnsType<FeedbackSummary> {
  return [
    { title: '问题摘要', dataIndex: 'question', ellipsis: true },
    { title: '原因', dataIndex: 'reason', width: 110, render: (value: FeedbackReason) => reasonLabels[value] },
    { title: '状态', dataIndex: 'status', width: 110, render: (value: FeedbackStatus) => <Tag color={statusColors[value]}>{statusLabels[value]}</Tag> },
    { title: '提交时间', dataIndex: 'createdAt', width: 190, render: (value: string) => new Date(value).toLocaleString('zh-CN') },
    { title: '操作', width: 100, fixed: 'right', render: (_, record) => <Button className="table-action-button" type="text" size="small" icon={<EyeOutlined />} onClick={() => onView(record.id)}>查看</Button> },
  ];
}
