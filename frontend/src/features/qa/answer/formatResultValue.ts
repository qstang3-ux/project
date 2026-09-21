import type { ResultColumn } from '../../../api/types';

export function formatResultValue(value: string | number | boolean | null | undefined, dataType: ResultColumn['dataType'], fieldKey?: string): string {
  if (value === null || value === undefined || value === '') return '--';
  if (dataType === 'boolean') return value ? '是' : '否';
  if (dataType === 'integer' || dataType === 'decimal') {
    const number = Number(value);
    if (dataType === 'integer' && fieldKey?.toLowerCase().includes('year')) return String(value);
    return Number.isFinite(number) ? new Intl.NumberFormat('zh-CN', { maximumFractionDigits: dataType === 'integer' ? 0 : 2 }).format(number) : String(value);
  }
  if (dataType === 'percent') {
    const number = Number(value);
    return Number.isFinite(number) ? `${new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(number)}%` : String(value);
  }
  if (dataType === 'date' || dataType === 'datetime') {
    const date = new Date(String(value));
    return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat('zh-CN', dataType === 'date' ? { dateStyle: 'medium' } : { dateStyle: 'medium', timeStyle: 'short' }).format(date);
  }
  return String(value);
}
