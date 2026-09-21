import { CheckCircleFilled, ClockCircleOutlined, CloseCircleOutlined, LoadingOutlined, QuestionCircleOutlined, RobotOutlined, SafetyCertificateOutlined, StopOutlined } from '@ant-design/icons';
import { Tag } from 'antd';
import type { ReactNode } from 'react';
import type { ExecutionDetail } from '../../../api/types';

const labels: Record<string, string> = {
  queued: '排队中',
  running: '执行中',
  awaiting_input: '待补充信息',
  completed: '已完成',
  failed: '执行失败',
  cancelled: '已停止',
  rejected: '安全拒绝',
};

const icons: Record<string, ReactNode> = {
  queued: <ClockCircleOutlined />,
  running: <LoadingOutlined spin />,
  awaiting_input: <QuestionCircleOutlined />,
  completed: <CheckCircleFilled />,
  failed: <CloseCircleOutlined />,
  cancelled: <StopOutlined />,
  rejected: <SafetyCertificateOutlined />,
};

export function AssistantMessageHeader({ status }: { status: ExecutionDetail['status'] }) {
  return (
    <div className="assistant-header">
      <span className="assistant-avatar"><RobotOutlined /></span>
      <div><strong>经管之星</strong><span>经营分析助手</span></div>
      <Tag className={`assistant-status assistant-status-${status}`}>{icons[status]}{labels[status] ?? '未知状态'}</Tag>
    </div>
  );
}
