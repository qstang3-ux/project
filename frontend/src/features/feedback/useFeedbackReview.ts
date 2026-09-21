import { App, Form } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../api/client';
import { getErrorMessage } from '../../api/errorMessages';
import { queryKeys } from '../../api/queryKeys';
import type { FeedbackDetail, FeedbackUpdate } from '../../api/types';
import type { FeedbackFilters } from './feedbackTypes';

export function useFeedbackReview() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [filterForm] = Form.useForm<FeedbackFilters>();
  const [updateForm] = Form.useForm<FeedbackUpdate>();
  const [filters, setFilters] = useState<FeedbackFilters>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedId, setSelectedId] = useState<string>();
  const [processOpen, setProcessOpen] = useState(false);
  const listQuery = useQuery({ queryKey: queryKeys.feedback({ ...filters, page, pageSize }), queryFn: () => api.listFeedback({ ...filters, page, pageSize }) });
  const detailQuery = useQuery({ queryKey: queryKeys.feedbackDetail(selectedId ?? 'none'), queryFn: () => api.getFeedback(selectedId ?? ''), enabled: Boolean(selectedId) });
  const updateMutation = useMutation({
    mutationFn: (values: FeedbackUpdate) => api.updateFeedback(selectedId ?? '', values),
    onSuccess: () => {
      setProcessOpen(false);
      void queryClient.invalidateQueries({ queryKey: queryKeys.feedbackRoot });
      void message.success('反馈处理结果已保存');
    },
    onError: (error) => void message.error(getErrorMessage(error)),
  });

  const applyFilters = (values: FeedbackFilters) => {
    setPage(1);
    setFilters(values);
  };

  const resetFilters = () => {
    filterForm.resetFields();
    setFilters({});
    setPage(1);
  };

  const openProcess = (detail: FeedbackDetail) => {
    updateForm.setFieldsValue({ status: detail.status, resolutionNote: detail.resolutionNote, version: detail.version });
    setProcessOpen(true);
  };

  return {
    filterForm,
    updateForm,
    filters,
    page,
    pageSize,
    list: listQuery.data,
    listLoading: listQuery.isLoading,
    listError: listQuery.error,
    retryList: listQuery.refetch,
    selectedId,
    detail: detailQuery.data,
    detailLoading: detailQuery.isLoading,
    detailError: detailQuery.error,
    retryDetail: detailQuery.refetch,
    processOpen,
    processing: updateMutation.isPending,
    applyFilters,
    resetFilters,
    selectFeedback: setSelectedId,
    closeDetail: () => setSelectedId(undefined),
    openProcess,
    closeProcess: () => setProcessOpen(false),
    saveProcess: (values: FeedbackUpdate) => updateMutation.mutate(values),
    changePage: (nextPage: number, nextPageSize: number) => { setPage(nextPage); setPageSize(nextPageSize); },
  };
}
