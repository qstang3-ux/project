import { CheckCircleFilled, CloseCircleFilled, LoadingOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { Collapse, Timeline, Typography } from 'antd';
import type { ExecutionDetail } from '../../../api/types';

const labels: Record<string, string> = {
  intent_classification: '识别问题意图',
  clarification_required: '等待补充信息',
  schema_selection: '选择数据表',
  sql_generation: '生成 SQL',
  sql_validation: '校验 SQL',
  query_execution: '执行查询',
  answer_generation: '生成回答',
};

const icon = (status: ExecutionDetail['steps'][number]['status']) => {
  if (status === 'completed') return <CheckCircleFilled className="step-success" />;
  if (status === 'failed') return <CloseCircleFilled className="step-failed" />;
  if (status === 'running') return <LoadingOutlined className="step-running" />;
  return <MinusCircleOutlined className="step-pending" />;
};

export function ExecutionSteps({ execution }: { execution: ExecutionDetail }) {
  const steps = execution.steps;
  return (
    <Collapse ghost size="small" items={[{
      key: 'steps',
      label: <span className="analysis-label">执行过程 <Typography.Text type="secondary">{steps.length} 步</Typography.Text></span>,
      children: <Timeline items={steps.map((step) => ({
        dot: icon(step.status),
        children: <div><strong>{labels[step.type] ?? '执行步骤'}</strong><p>{step.summary}{step.durationMs !== null && step.durationMs !== undefined && step.durationMs > 0 ? ` · ${String(step.durationMs)}ms` : ''}</p></div>,
      }))} />,
    }]} />
  );
}
