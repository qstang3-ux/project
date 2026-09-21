import type { ResultColumn } from '../../../api/types';

const technicalLabelPattern = /(^|\s)(id|uuid|guid|pk)(\s|$)|唯一标识|内部编号|主键/i;

function normalizeKey(key: string) {
  return key
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/[\s-]+/g, '_')
    .toLowerCase();
}

export function isTechnicalResultColumn(column: ResultColumn) {
  const key = normalizeKey(column.key);
  const isIdentifier = /(^|_)(id|uuid|guid|pk)$/.test(key);
  const isRowIndex = /^(row_?(number|num|index)|rn)$/.test(key);

  return isIdentifier || isRowIndex || technicalLabelPattern.test(column.label.trim());
}

export function getVisibleResultColumns(columns: ResultColumn[]) {
  return columns.filter((column) => !isTechnicalResultColumn(column));
}
