import { QuestionCircleOutlined } from '@ant-design/icons';
import type { ExecutionDetail } from '../../../api/types';
import { ExecutionContext } from './ExecutionContext';

const slotLabels: Record<string, string> = {
  metric: '指标口径',
  指标: '指标口径',
  dimension: '分析维度',
  维度: '分析维度',
  time_range: '时间范围',
  时间范围: '时间范围',
  year: '分析年份',
  年份: '分析年份',
  business_unit: '经营单元',
  经营单元: '经营单元',
  comparison_basis: '比较基准',
  比较基准: '比较基准',
};

interface ClarificationPromptProps {
  clarification: ExecutionDetail['clarification'];
  intent: ExecutionDetail['intent'];
  normalizedQuestion: ExecutionDetail['normalizedQuestion'];
  missingSlots: string[];
  clarificationRound: number;
}

export function ClarificationPrompt({ clarification, intent, normalizedQuestion, missingSlots, clarificationRound }: ClarificationPromptProps) {
  const prompt = clarification?.prompt ?? '请补充完成本次分析所需的信息。';
  const round = clarification?.round ?? clarificationRound;
  const maxRounds = clarification?.maxRounds ?? 2;
  const slots = clarification?.missingSlots ?? missingSlots;

  return (
    <section className="clarification-prompt" role="status" aria-live="polite">
      <div className="clarification-heading">
        <span className="clarification-icon" aria-hidden="true"><QuestionCircleOutlined /></span>
        <div className="clarification-copy">
          <span className="clarification-eyebrow">需要补充信息</span>
          <p>{prompt}</p>
        </div>
        <span className="clarification-round">{round} / {maxRounds}</span>
      </div>
      {slots.length ? (
        <div className="clarification-slots" aria-label="建议补充内容">
          <span>建议补充</span>
          {slots.map((slot) => <b key={slot}>{slotLabels[slot] ?? slot}</b>)}
        </div>
      ) : null}
      <ExecutionContext intent={intent} normalizedQuestion={normalizedQuestion} round={round} maxRounds={maxRounds} />
    </section>
  );
}
