import type { ChartSpec, ResultColumn, ResultSet } from '../../../api/types';

export type SwitchableChartType = 'bar' | 'line' | 'pie';

export interface ChartViewOption {
  type: SwitchableChartType;
  chart: ChartSpec | null;
  enabled: boolean;
  reason?: string;
}

const numericTypes = new Set(['decimal', 'integer', 'percent']);
const identifierHint = /(^|_)(id|code)$/i;

function firstCategory(columns: ResultColumn[]): string | undefined {
  return columns.find((column) => !numericTypes.has(column.dataType) && !identifierHint.test(column.key))?.key
    ?? columns.find((column) => !numericTypes.has(column.dataType))?.key;
}

function numericFields(columns: ResultColumn[]): string[] {
  return columns.filter((column) => numericTypes.has(column.dataType) && !/(^|_)(year|month|quarter)$/i.test(column.key)).map((column) => column.key);
}

export function buildChartViewOptions(chart: ChartSpec, result: ResultSet): ChartViewOption[] {
  const categoryField = chart.xField ?? chart.nameField ?? firstCategory(result.columns);
  const measures = chart.yFields?.length ? chart.yFields : chart.valueField ? [chart.valueField] : numericFields(result.columns);
  const firstMeasure = measures[0];
  const cartesianReady = Boolean(categoryField && measures.length);
  const pieReady = Boolean(categoryField && firstMeasure) && result.rows.length <= 12;
  const common = { title: chart.title, unit: chart.unit };

  return [
    {
      type: 'bar',
      enabled: cartesianReady,
      reason: cartesianReady ? undefined : '缺少分类字段或数值字段',
      chart: cartesianReady ? { ...common, type: 'bar', xField: categoryField, yFields: measures, nameField: null, valueField: null } : null,
    },
    {
      type: 'line',
      enabled: cartesianReady,
      reason: cartesianReady ? undefined : '缺少分类字段或数值字段',
      chart: cartesianReady ? { ...common, type: 'line', xField: categoryField, yFields: measures, nameField: null, valueField: null } : null,
    },
    {
      type: 'pie',
      enabled: pieReady,
      reason: !categoryField || !firstMeasure ? '缺少分类字段或数值字段' : '分类超过 12 项，不适合饼图',
      chart: pieReady ? { ...common, type: 'pie', nameField: categoryField, valueField: firstMeasure, xField: null, yFields: [] } : null,
    },
  ];
}
