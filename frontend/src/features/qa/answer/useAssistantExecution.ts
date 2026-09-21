import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';
import { useCallback, useRef, useState } from 'react';
import { api } from '../../../api/client';
import { getErrorMessage } from '../../../api/errorMessages';
import { createClarificationIdempotencyKey } from '../../../api/idempotency';
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
  const queryClient = useQueryClient();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const clarificationSubmittingRef = useRef(false);
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
  const clarificationMutation = useMutation({
    mutationFn: (content: string) => {
      const round = executionQuery.data?.clarification?.round ?? executionQuery.data?.clarificationRound ?? 0;
      const idempotencyKey = createClarificationIdempotencyKey(executionId, round, content);
      return api.submitClarification(executionId, { content }, idempotencyKey);
    },
    onSuccess: async () => {
      void message.success('补充信息已提交，正在继续分析。');
      const refreshed = await refetchExecution();
      const sessionId = refreshed.data?.sessionId;
      if (sessionId) await queryClient.invalidateQueries({ queryKey: queryKeys.messages(sessionId) });
    },
    onError: (error) => void message.error(getErrorMessage(error)),
  });
  const cancelMutation = useMutation({
    mutationFn: () => api.cancelExecution(executionId),
    onSuccess: async () => {
      void message.success('本次问数已停止。');
      const refreshed = await refetchExecution();
      const sessionId = refreshed.data?.sessionId;
      if (sessionId) await queryClient.invalidateQueries({ queryKey: queryKeys.messages(sessionId) });
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

  const submitClarification = useCallback((content: string) => {
    if (clarificationSubmittingRef.current) return;
    clarificationSubmittingRef.current = true;
    clarificationMutation.mutate(content, {
      onSettled: () => {
        clarificationSubmittingRef.current = false;
      },
    });
  }, [clarificationMutation]);

  return { executionQuery, feedbackOpen, setFeedbackOpen, versionsOpen, setVersionsOpen, feedbackMutation, clarificationMutation, submitClarification, cancelMutation, exportMutation };
}
