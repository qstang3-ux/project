import { Alert, Table, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { ResultSet } from '../../../api/types';
import { formatResultValue } from './formatResultValue';
import { getResultColumnLabel } from './resultColumnLabel';
import { getVisibleResultColumns } from './resultColumnVisibility';

interface ResultRow { key: string; [column: string]: string | number | boolean | null }

interface ResultTableProps {
  result: ResultSet;
  highlightedRowIndex?: number | null;
  onHighlightRow?: (index: number | null) => void;
}

export function ResultTable({ result, highlightedRowIndex = null, onHighlightRow }: ResultTableProps) {
  const rows: ResultRow[] = result.rows.map((row, index) => ({ key: String(index), ...row }));
  const visibleResultColumns = getVisibleResultColumns(result.columns);
  const columns: ColumnsType<ResultRow> = visibleResultColumns.map((column) => ({
    title: column.unit ? `${getResultColumnLabel(column)}（${column.unit}）` : getResultColumnLabel(column),
    dataIndex: column.key,
    key: column.key,
    ellipsis: true,
    align: column.dataType === 'decimal' || column.dataType === 'integer' || column.dataType === 'percent' ? 'right' : column.dataType === 'date' ? 'center' : 'left',
    className: column.dataType === 'decimal' || column.dataType === 'integer' || column.dataType === 'percent' ? 'result-column-number' : undefined,
    sorter: (left, right) => String(left[column.key] ?? '').localeCompare(String(right[column.key] ?? ''), 'zh-CN', { numeric: true }),
    render: (value: ResultRow[string]) => <Typography.Text>{formatResultValue(value, column.dataType, column.key)}</Typography.Text>,
  }));

  if (result.rowCount === 0) return <Alert type="info" showIcon message="查询完成，但没有匹配的数据" description="可以调整时间范围、经营单元或数据源后重试。" />;
  return (
    <section className="result-section">
      <div className="section-heading"><h3>查询结果</h3><span>{result.rowCount} 行</span></div>
      {result.truncated ? <Alert banner type="warning" message={`结果较多，仅展示前 ${String(result.rows.length)} 条。`} /> : null}
      {visibleResultColumns.length > 0 ? (
        <Table<ResultRow>
          size="middle"
          columns={columns}
          dataSource={rows}
          pagination={false}
          scroll={{ x: 'max-content' }}
          rowClassName={(_, index) => index === highlightedRowIndex ? 'result-row-highlighted' : ''}
          onRow={(_, index) => ({
            tabIndex: 0,
            onMouseEnter: () => onHighlightRow?.(index ?? null),
            onMouseLeave: () => onHighlightRow?.(null),
            onFocus: () => onHighlightRow?.(index ?? null),
            onBlur: () => onHighlightRow?.(null),
          })}
        />
      ) : (
        <Alert type="info" showIcon message="查询结果仅包含内部标识字段" description="这些字段已隐藏，请调整问题以返回名称、状态、金额等业务信息。" />
      )}
    </section>
  );
}
