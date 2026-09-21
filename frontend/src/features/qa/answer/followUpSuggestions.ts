import type { ChartSpec } from '../../../api/types';

const fallbackByChart: Record<ChartSpec['type'], string[]> = {
  bar: ['查看排名靠后的经营单元', '解释本次查询的指标口径'],
  line: ['对比上一周期的变化', '解释趋势变化最大的时间点'],
  pie: ['查看各分类的详细金额', '解释占比最高分类的指标口径'],
  metric: ['查看该指标的时间趋势', '解释该指标的统计口径'],
  none: ['解释本次查询的指标口径'],
};

export function contextualFollowUps(questions: string[], chart?: ChartSpec | null): string[] {
  const candidates = questions.length ? questions : fallbackByChart[chart?.type ?? 'none'];
  return [...new Set(candidates.map((question) => question.trim()).filter(Boolean))].slice(0, 3);
}
