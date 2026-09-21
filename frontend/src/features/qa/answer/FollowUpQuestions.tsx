import { Button } from 'antd';
import { ArrowRightOutlined } from '@ant-design/icons';
import type { ChartSpec } from '../../../api/types';
import { contextualFollowUps } from './followUpSuggestions';

export function FollowUpQuestions({ questions, chart, onSelect }: { questions: string[]; chart?: ChartSpec | null; onSelect: (question: string) => void }) {
  const suggestions = contextualFollowUps(questions, chart);
  if (!suggestions.length) return null;
  return (
    <div className="follow-ups">
      <span>继续探索</span>
      {suggestions.map((question) => <Button className="suggestion-button" key={question} onClick={() => onSelect(question)}>{question}<ArrowRightOutlined /></Button>)}
    </div>
  );
}
