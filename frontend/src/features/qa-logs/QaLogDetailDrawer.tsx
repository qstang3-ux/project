import { Button, Descriptions, Drawer, Result, Skeleton, Space, Table, Tag } from 'antd';
import { getErrorMessage } from '../../api/errorMessages';
import type { QaLogDetail } from '../../api/types';
import { CopyButton } from '../../components/CopyButton';
import { executionStatusColors, executionStatusLabels, modelPurposeLabels } from './qaLogPresentation';

export function QaLogDetailDrawer(props: { open: boolean; detail?: QaLogDetail; loading: boolean; error: unknown; onClose: () => void; onRetry: () => void }) {
  return <Drawer title="问答日志详情" width={760} open={props.open} onClose={props.onClose}>
    {props.loading ? <Skeleton active paragraph={{ rows: 12 }} /> : null}
    {props.error ? <Result status="error" title="日志详情加载失败" subTitle={getErrorMessage(props.error)} extra={<Button onClick={props.onRetry}>重试</Button>} /> : null}
    {props.detail ? <QaLogDetailContent detail={props.detail} /> : null}
  </Drawer>;
}

function QaLogDetailContent({ detail }: { detail: QaLogDetail }) {
  const tokenUsage = detail.tokenUsage;
  return <div className="qa-log-detail">
    <Descriptions bordered column={1} size="small" items={[
      { key: 'execution', label: '执行 ID', children: <Space>{detail.executionId}<CopyButton text={detail.executionId} label="复制执行 ID" /></Space> },
      { key: 'request', label: '请求 ID', children: <Space>{detail.requestId}<CopyButton text={detail.requestId} label="复制请求 ID" /></Space> },
      { key: 'question', label: '用户问题', children: <Space>{detail.question}<CopyButton text={detail.question} label="复制问题" /></Space> },
      { key: 'status', label: '状态', children: <Tag color={executionStatusColors[detail.status]}>{executionStatusLabels[detail.status]}</Tag> },
      { key: 'intent', label: '识别意图', children: detail.intent ?? '--' },
      { key: 'normalized', label: '规范化问题', children: detail.normalizedQuestion ?? '--' },
      { key: 'source', label: '数据源', children: detail.dataSourceNames.join('、') || '--' },
      { key: 'objects', label: '查询对象', children: detail.selectedObjects.join('、') || '--' },
      { key: 'validation', label: '校验摘要', children: detail.validationSummary ?? '--' },
      { key: 'tokens', label: 'Token', children: tokenUsage ? `输入 ${String(tokenUsage.promptTokens)} / 输出 ${String(tokenUsage.completionTokens)} / 总计 ${String(tokenUsage.totalTokens)}` : '--' },
      { key: 'graph', label: 'Agent 图', children: `${detail.graphVersion ?? '--'} · ${detail.checkpointStatus ?? '--'}` },
      { key: 'rag', label: 'RAG', children: `${String(detail.ragDocumentIds.length)} 个文档${detail.ragDegraded ? '（已降级）' : ''}` },
      { key: 'error', label: '错误', children: detail.errorMessage ?? detail.errorCode ?? '--' },
    ]} />
    {detail.executedSql ?? detail.generatedSql ? <section><h3>SQL</h3><pre className="mono qa-log-sql">{detail.executedSql ?? detail.generatedSql}</pre></section> : null}
    <section><h3>模型调用</h3><Table size="small" rowKey={(record) => `${record.purpose}-${String(record.durationMs)}`} pagination={false} dataSource={detail.modelCalls} columns={[
      { title: '用途', dataIndex: 'purpose', render: (value: string) => modelPurposeLabels[value] ?? value },
      { title: '模型', dataIndex: 'model', ellipsis: true },
      { title: '耗时', dataIndex: 'durationMs', width: 90, render: (value: number) => `${String(value)}ms` },
      { title: 'Token', dataIndex: 'totalTokens', width: 85 },
      { title: '状态', dataIndex: 'status', width: 100, render: (value: string) => <Tag color={value === 'success' ? 'success' : 'error'}>{value}</Tag> },
    ]} /></section>
    <section><h3>节点轨迹</h3><div className="qa-log-trace">{detail.graphNodeTrace.map((node, index) => <Tag key={`${node}-${String(index)}`}>{index + 1}. {node}</Tag>)}</div></section>
  </div>;
}
