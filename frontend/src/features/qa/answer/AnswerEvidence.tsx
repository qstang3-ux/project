import { DownOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Collapse } from 'antd';
import type { ExecutionDetail } from '../../../api/types';

export function AnswerEvidence({ execution }: { execution: ExecutionDetail }) {
  if (execution.status !== 'completed') return null;
  const objects = execution.selectedObjects ?? [];
  const items = [{
    key: 'evidence',
    label: <span className="answer-evidence-label"><InfoCircleOutlined /> 为什么是这个答案</span>,
    children: (
      <div className="answer-evidence-grid">
        <div><span>理解的问题</span><strong>{execution.normalizedQuestion || execution.question}</strong></div>
        <div><span>数据范围</span><strong>{String(execution.dataSourceIds.length)} 个已授权数据源</strong></div>
        <div><span>查询对象</span><strong>{objects.length ? objects.join('、') : '未使用数据库查询'}</strong></div>
        <div><span>结果依据</span><strong>{execution.result ? `${String(execution.result.rowCount)} 行查询结果` : '受控回答上下文'}</strong></div>
      </div>
    ),
  }];
  return <Collapse className="answer-evidence" ghost items={items} expandIconPosition="end" expandIcon={({ isActive }) => <DownOutlined rotate={isActive ? 180 : 0} />} />;
}
