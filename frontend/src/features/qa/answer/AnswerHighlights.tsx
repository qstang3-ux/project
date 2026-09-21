import type { ResultSet } from '../../../api/types';
import { buildAnswerHighlights } from './buildAnswerHighlights';

export function AnswerHighlights({ result }: { result: ResultSet }) {
  const highlights = buildAnswerHighlights(result);
  if (!highlights.length) return null;
  return (
    <section className="answer-highlights" aria-label="答案要点">
      {highlights.map((item) => (
        <div key={`${item.label}-${item.value}`}>
          <span>{item.label}</span>
          <strong title={item.value}>{item.value}</strong>
        </div>
      ))}
    </section>
  );
}
