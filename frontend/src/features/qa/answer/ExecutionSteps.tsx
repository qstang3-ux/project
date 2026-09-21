import { CheckCircleFilled, CloseCircleFilled, LoadingOutlined, MinusCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { Collapse } from 'antd';
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

const statusLabel = (status: ExecutionDetail['steps'][number]['status']) => ({
  completed: '已完成',
  failed: '未通过',
  running: '处理中',
  pending: '等待中',
  skipped: '已跳过',
}[status]);

const formatDuration = (durationMs: number | null | undefined) => {
  if (durationMs === null || durationMs === undefined) return null;
  if (durationMs < 1) return '<1ms';
  if (durationMs < 1000) return `${String(durationMs)}ms`;
  return `${(durationMs / 1000).toFixed(durationMs >= 10000 ? 1 : 2)}s`;
};

export function ExecutionSteps({ execution }: { execution: ExecutionDetail }) {
  const steps = execution.steps;
  const completedCount = steps.filter((step) => step.status === 'completed').length;
  const durationMs = steps.reduce((total, step) => total + (step.durationMs ?? 0), 0);
  const durationLabel = durationMs > 0 ? formatDuration(durationMs) : null;
  return (
    <Collapse className="execution-steps" ghost items={[{
      key: 'steps',
      label: (
        <span className="execution-steps-heading">
          <span className="execution-steps-heading-icon"><ThunderboltOutlined /></span>
          <span className="execution-steps-heading-copy"><strong>执行过程</strong><small>查看本次分析的处理链路</small></span>
          <span className="execution-steps-heading-meta"><b>{completedCount}/{steps.length}</b> 已完成{durationLabel ? <i>·</i> : null}{durationLabel ? <b>{durationLabel}</b> : null}</span>
        </span>
      ),
      children: (
        <ol className="execution-step-list">
          {steps.map((step, index) => {
            const stepDuration = formatDuration(step.durationMs);
            return (
              <li className={`execution-step execution-step-${step.status}`} key={`${step.type}-${String(index)}`}>
                <span className="execution-step-marker" aria-hidden="true">{icon(step.status)}</span>
                <span className="execution-step-index">{String(index + 1).padStart(2, '0')}</span>
                <span className="execution-step-copy"><strong>{labels[step.type] ?? '执行步骤'}</strong><small>{step.summary}</small></span>
                <span className="execution-step-meta"><em>{statusLabel(step.status)}</em>{stepDuration ? <time>{stepDuration}</time> : null}</span>
              </li>
            );
          })}
        </ol>
      ),
    }]} />
  );
}
