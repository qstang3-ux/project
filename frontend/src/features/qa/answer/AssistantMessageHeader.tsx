import { RobotOutlined } from '@ant-design/icons';
import { Tag } from 'antd';
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

export function AssistantMessageHeader({ status }: { status: ExecutionDetail['status'] }) {
  return (
    <div className="assistant-header">
      <span className="assistant-avatar"><RobotOutlined /></span>
      <div><strong>经管之星</strong><span>经营分析助手</span></div>
      <Tag className={`assistant-status assistant-status-${status}`}><i aria-hidden="true" />{labels[status] ?? '未知状态'}</Tag>
    </div>
  );
}
