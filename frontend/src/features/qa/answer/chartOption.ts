import type { EChartsCoreOption } from 'echarts/core';
import type { ChartSpec, ResultSet } from '../../../api/types';
import { getResultColumnLabel } from './resultColumnLabel';

const colors = ['#2F54EB', '#16A394', '#F59E0B', '#7C3AED', '#D9367E'];

const VISIBLE_CATEGORY_COUNT = 10;

function getCategoryLayout(categories: string[]) {
  const longestLabelLength = Math.max(0, ...categories.map((category) => category.length));
  const needsRotation = categories.length > 6 || longestLabelLength > 6;
  const needsZoom = categories.length > VISIBLE_CATEGORY_COUNT;

  return {
    gridBottom: needsZoom ? 104 : needsRotation ? 78 : 54,
    axisLabel: {
      interval: 'auto' as const,
      hideOverlap: true,
      rotate: needsRotation ? 28 : 0,
      margin: 14,
      width: needsRotation ? 96 : 120,
      overflow: 'truncate' as const,
      color: '#667085',
    },
    dataZoom: needsZoom
      ? [
          { type: 'inside' as const, xAxisIndex: 0, filterMode: 'none' as const, start: 0, end: (VISIBLE_CATEGORY_COUNT / categories.length) * 100 },
          { type: 'slider' as const, xAxisIndex: 0, filterMode: 'none' as const, start: 0, end: (VISIBLE_CATEGORY_COUNT / categories.length) * 100, bottom: 8, height: 18, borderColor: '#E4E7EC', fillerColor: 'rgba(47, 84, 235, .12)', handleStyle: { color: '#2F54EB' }, moveHandleStyle: { color: '#8095D9' } },
        ]
      : undefined,
  };
}

export function buildChartOption(chart: ChartSpec, result: ResultSet): EChartsCoreOption | null {
  const title = { text: chart.title ?? '数据可视化', left: 8, textStyle: { fontSize: 16, color: '#111827' } };
  const tooltip = { trigger: chart.type === 'pie' ? 'item' as const : 'axis' as const, valueFormatter: (value: unknown) => `${String(value)}${chart.unit ?? ''}` };
  if (chart.type === 'pie') {
    if (!chart.nameField || !chart.valueField) return null;
    return { color: colors, title, tooltip, legend: { bottom: 0 }, series: [{ type: 'pie', radius: ['38%', '68%'], data: result.rows.map((row) => ({ name: String(row[chart.nameField ?? ''] ?? '--'), value: Number(row[chart.valueField ?? ''] ?? 0) })), label: { formatter: '{b}: {d}%' } }] };
  }
  if (!chart.xField || !chart.yFields?.length) return null;
  const seriesType: 'bar' | 'line' = chart.type === 'line' ? 'line' : 'bar';
  const categories = result.rows.map((row) => String(row[chart.xField ?? ''] ?? '--'));
  const categoryLayout = getCategoryLayout(categories);
  return {
    color: colors,
    title,
    tooltip,
    legend: { top: 30 },
    grid: { left: 70, right: 24, top: 72, bottom: categoryLayout.gridBottom },
    xAxis: { type: 'category', data: categories, axisTick: { alignWithLabel: true }, axisLabel: categoryLayout.axisLabel },
    yAxis: { type: 'value', name: chart.unit ?? undefined, splitLine: { lineStyle: { color: '#EEF0F4' } } },
    dataZoom: categoryLayout.dataZoom,
    series: chart.yFields.map((field) => {
      const column = result.columns.find((item) => item.key === field);
      return { name: column ? getResultColumnLabel(column) : field, type: seriesType, smooth: seriesType === 'line', data: result.rows.map((row) => Number(row[field] ?? 0)), barMaxWidth: 44 };
    }),
  };
}
