import type { ResultColumn, ResultSet } from '../../../api/types';
import { formatResultValue } from './formatResultValue';
import { getResultColumnLabel } from './resultColumnLabel';
import { getVisibleResultColumns } from './resultColumnVisibility';

export interface AnswerHighlight {
  label: string;
  value: string;
}

const numericTypes = new Set(['decimal', 'integer', 'percent']);
const dimensionHint = /(name|business_unit|product_line|industry|region|stage|status)/i;
const technicalHint = /(^|_)(id|code)$/i;
const timeHint = /(^|_)(year|month|quarter|date)$/i;

function firstDimension(columns: ResultColumn[]): ResultColumn | undefined {
  return columns.find((column) => dimensionHint.test(column.key) && !technicalHint.test(column.key))
    ?? columns.find((column) => !numericTypes.has(column.dataType) && !technicalHint.test(column.key));
}

export function buildAnswerHighlights(result: ResultSet): AnswerHighlight[] {
  const firstRow = result.rows[0];
  if (!firstRow) return [];
  const visibleColumns = getVisibleResultColumns(result.columns);
  const dimension = firstDimension(visibleColumns);
  const measures = visibleColumns.filter((column) => numericTypes.has(column.dataType) && !timeHint.test(column.key));
  const highlights: AnswerHighlight[] = [];

  if (dimension) {
    highlights.push({
      label: '首条结果',
      value: formatResultValue(firstRow[dimension.key], dimension.dataType, dimension.key),
    });
  }

  for (const measure of measures.slice(0, dimension ? 1 : 2)) {
    highlights.push({
      label: getResultColumnLabel(measure),
      value: formatResultValue(firstRow[measure.key], measure.dataType, measure.key),
    });
  }

  highlights.push({ label: result.truncated ? '当前展示' : '结果规模', value: `${String(result.rows.length)} / ${String(result.rowCount)} 行` });
  return highlights.slice(0, 3);
}
