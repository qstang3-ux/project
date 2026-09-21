import { QuestionCircleOutlined, SendOutlined, StopOutlined } from '@ant-design/icons';
import { Alert, Button, Input, Popconfirm, Space, Tag } from 'antd';
import { useState } from 'react';
import type { ExecutionDetail } from '../../../api/types';
import { ExecutionContext } from './ExecutionContext';

interface ClarificationPromptProps {
  clarification: ExecutionDetail['clarification'];
  intent: ExecutionDetail['intent'];
  normalizedQuestion: ExecutionDetail['normalizedQuestion'];
  missingSlots: string[];
  clarificationRound: number;
  submitting: boolean;
  cancelling: boolean;
  onSubmit: (content: string) => void;
  onCancel: () => void;
}

export function ClarificationPrompt({ clarification, intent, normalizedQuestion, missingSlots, clarificationRound, submitting, cancelling, onSubmit, onCancel }: ClarificationPromptProps) {
  const [content, setContent] = useState('');
  const prompt = clarification?.prompt ?? '请补充完成本次分析所需的信息。';
  const round = clarification?.round ?? clarificationRound;
  const maxRounds = clarification?.maxRounds ?? 2;
  const slots = clarification?.missingSlots ?? missingSlots;

  return (
    <section className="clarification-prompt">
      <Alert type="warning" showIcon icon={<QuestionCircleOutlined />} message={prompt} description={slots.length ? <Space size={[6, 6]} wrap><span>待补充</span>{slots.map((slot) => <Tag key={slot}>{slot}</Tag>)}</Space> : undefined} />
      <ExecutionContext intent={intent} normalizedQuestion={normalizedQuestion} round={round} maxRounds={maxRounds} />
      <div className="clarification-input">
        <Input.TextArea aria-label="补充信息" value={content} onChange={(event) => setContent(event.target.value)} rows={2} maxLength={2000} showCount disabled={submitting || cancelling} placeholder="补充时间范围、经营单元或指标口径" />
        <Space>
          <Popconfirm title="停止本次问数？" description="已补充的内容不会继续执行。" okText="停止" cancelText="继续填写" okButtonProps={{ danger: true }} onConfirm={onCancel}>
            <Button icon={<StopOutlined />} aria-label="停止" danger disabled={submitting} loading={cancelling}>停止</Button>
          </Popconfirm>
          <Button type="primary" icon={<SendOutlined />} aria-label="提交并继续" loading={submitting} disabled={cancelling || !content.trim()} onClick={() => onSubmit(content.trim())}>提交并继续</Button>
        </Space>
      </div>
    </section>
  );
}
