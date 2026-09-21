import { useMutation, useQuery } from '@tanstack/react-query';
import { App } from 'antd';
import { useCallback, useState } from 'react';
import { api } from '../../../api/client';
import { getErrorMessage } from '../../../api/errorMessages';
import { queryKeys } from '../../../api/queryKeys';
import type { ExecutionDetail, FeedbackReason } from '../../../api/types';
import { useExecutionEventRefresh } from './useExecutionEventRefresh';

interface FeedbackInput {
  execution: ExecutionDetail;
  reason: FeedbackReason;
  description?: string;
}

export function useAssistantExecution(executionId: string, preview?: ExecutionDetail) {
  const { message } = App.useApp();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const executionQuery = useQuery({
    queryKey: queryKeys.execution(executionId),
    queryFn: () => api.getExecution(executionId),
    initialData: preview,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'queued' || status === 'running' ? 1000 : false;
    },
  });
  const refetchExecution = executionQuery.refetch;
  const refreshExecution = useCallback(() => {
    void refetchExecution();
  }, [refetchExecution]);
  useExecutionEventRefresh(executionId, executionQuery.data?.status, refreshExecution);
  const feedbackMutation = useMutation({
    mutationFn: ({ execution, reason, description }: FeedbackInput) => {
      if (!execution.assistantMessageId) throw new Error('缺少回答消息 ID');
      return api.createFeedback({ sessionId: execution.sessionId, assistantMessageId: execution.assistantMessageId, executionId: execution.id, reason, description });
    },
    onSuccess: () => {
      setFeedbackOpen(false);
      void message.success('反馈已提交，感谢你的校对。');
    },
    onError: (error) => void message.error(getErrorMessage(error)),
  });
  const exportMutation = useMutation({
    mutationFn: () => api.exportExecutionCsv(executionId),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      void message.success('查询结果已导出。');
    },
    onError: (error) => void message.error(getErrorMessage(error)),
  });

  return { executionQuery, feedbackOpen, setFeedbackOpen, versionsOpen, setVersionsOpen, feedbackMutation, exportMutation };
}
