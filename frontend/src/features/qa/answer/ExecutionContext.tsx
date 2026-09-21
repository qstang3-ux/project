import type { ExecutionDetail } from '../../../api/types';

const intentLabels: Record<string, string> = {
  data_query: '数据查询',
  clarification: '信息待确认',
  business_definition: '业务口径',
  product_help: '产品帮助',
  chat: '普通对话',
  out_of_scope: '超出范围',
  unsafe: '安全拒绝',
};

interface ExecutionContextProps {
  intent: ExecutionDetail['intent'];
  normalizedQuestion: ExecutionDetail['normalizedQuestion'];
  round: number;
  maxRounds: number;
}

export function ExecutionContext({ intent, normalizedQuestion, round, maxRounds }: ExecutionContextProps) {
  return (
    <div className="clarification-context" aria-label="问题识别结果">
      <div className="clarification-context-question"><span>当前理解</span><strong>{normalizedQuestion ?? '等待补充后确认问题'}</strong></div>
      <div className="clarification-context-meta">
        <span><i aria-hidden="true" />{intent ? intentLabels[intent] ?? '未知意图' : '待确认'}</span>
        <span>第 {round} / {maxRounds} 轮</span>
      </div>
    </div>
  );
}
