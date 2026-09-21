import { Card, Form } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../api/client';
import { queryKeys } from '../../api/queryKeys';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { QaLogDetailDrawer } from './QaLogDetailDrawer';
import { QaLogFilter, type QaLogFilterValues } from './QaLogFilter';
import { QaLogTable } from './QaLogTable';

export function QaLogReview() {
  const [form] = Form.useForm<QaLogFilterValues>();
  const [filters, setFilters] = useState<Omit<QaLogFilterValues, 'range'> & { from?: string; to?: string }>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedId, setSelectedId] = useState<string>();
  const listQuery = useQuery({ queryKey: queryKeys.qaLogs({ ...filters, page, pageSize }), queryFn: () => api.listQaLogs({ ...filters, page, pageSize }) });
  const detailQuery = useQuery({ queryKey: queryKeys.qaLogDetail(selectedId ?? 'none'), queryFn: () => api.getQaLog(selectedId ?? ''), enabled: Boolean(selectedId) });
  const applyFilters = (values: QaLogFilterValues) => {
    setPage(1);
    setFilters({ keyword: values.keyword, userId: values.userId, status: values.status, from: values.range?.[0].toISOString(), to: values.range?.[1].toISOString() });
  };
  const reset = () => { form.resetFields(); setFilters({}); setPage(1); };
  return <div className="page-shell settings-page qa-log-page">
    <div className="page-heading"><h1>问答日志</h1><p>查看每次问答的意图、SQL、模型调用、Token、Agent节点和执行结果。</p></div>
    <Card><QaLogFilter form={form} onSubmit={applyFilters} onReset={reset} /></Card>
    <Card>
      {listQuery.isError ? <ErrorState title="问答日志加载失败" error={listQuery.error} onRetry={() => void listQuery.refetch()} /> : null}
      {!listQuery.isError && !listQuery.isLoading && (listQuery.data?.items.length ?? 0) === 0 ? <EmptyState title="暂无符合条件的问答日志" description="调整筛选条件后重试。" /> : <QaLogTable items={listQuery.data?.items ?? []} loading={listQuery.isLoading} page={page} pageSize={pageSize} total={listQuery.data?.page.total ?? 0} onPageChange={(next, size) => { setPage(next); setPageSize(size); }} onView={setSelectedId} />}
    </Card>
    <QaLogDetailDrawer open={Boolean(selectedId)} detail={detailQuery.data} loading={detailQuery.isLoading} error={detailQuery.error} onClose={() => setSelectedId(undefined)} onRetry={() => void detailQuery.refetch()} />
  </div>;
}
