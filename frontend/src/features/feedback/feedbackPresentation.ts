import type { FeedbackReason, FeedbackStatus } from '../../api/types';

export const reasonLabels: Record<FeedbackReason, string> = {
  sql_error: 'SQL 错误',
  result_error: '结果错误',
  metric_error: '口径错误',
  answer_error: '回答错误',
  other: '其他',
};

export const statusLabels: Record<FeedbackStatus, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  ignored: '已忽略',
};

export const statusColors: Record<FeedbackStatus, string> = {
  pending: 'orange',
  processing: 'blue',
  resolved: 'green',
  ignored: 'default',
};
