import { Button, Descriptions, Drawer, Result, Skeleton, Space, Tag } from 'antd';
import { getErrorMessage } from '../../api/errorMessages';
import type { FeedbackDetail } from '../../api/types';
import { CopyButton } from '../../components/CopyButton';
import { reasonLabels, statusColors, statusLabels } from './feedbackPresentation';

interface FeedbackDetailDrawerProps {
  open: boolean;
  detail?: FeedbackDetail;
  loading: boolean;
  error: unknown;
  onClose: () => void;
  onRetry: () => void;
  onProcess: (detail: FeedbackDetail) => void;
}

export function FeedbackDetailDrawer(props: FeedbackDetailDrawerProps) {
  const detail = props.detail;
  return (
    <Drawer title="反馈详情" width={680} open={props.open} onClose={props.onClose} extra={detail ? <Button type="primary" onClick={() => props.onProcess(detail)}>处理反馈</Button> : null}>
      {props.loading ? <Skeleton active paragraph={{ rows: 10 }} /> : null}
      {props.error ? <Result status="error" title="反馈详情加载失败" subTitle={getErrorMessage(props.error)} extra={<Button onClick={props.onRetry}>重试</Button>} /> : null}
      {detail ? <FeedbackDetailContent detail={detail} /> : null}
    </Drawer>
  );
}

function FeedbackDetailContent({ detail }: { detail: FeedbackDetail }) {
  return <Descriptions bordered column={1} size="small" items={[
    { key: 'question', label: '用户问题', children: <Space>{detail.question}<CopyButton text={detail.question} /></Space> },
    { key: 'sources', label: '数据源', children: detail.dataSourceNames?.join('、') || '--' },
    { key: 'answer', label: 'AI 回答', children: <div>{detail.answer}<CopyButton text={detail.answer} /></div> },
    { key: 'sql', label: '生成 SQL', children: detail.sql ? <pre className="mono">{detail.sql}</pre> : '--' },
    { key: 'summary', label: '结果摘要', children: detail.resultSummary ?? '--' },
    { key: 'model', label: '使用模型', children: detail.modelName ?? '--' },
    { key: 'reason', label: '反馈原因', children: reasonLabels[detail.reason] },
    { key: 'description', label: '反馈说明', children: detail.description ?? '--' },
    { key: 'status', label: '处理状态', children: <Tag color={statusColors[detail.status]}>{statusLabels[detail.status]}</Tag> },
    { key: 'note', label: '处理备注', children: detail.resolutionNote ?? '--' },
  ]} />;
}
