import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { createClarificationIdempotencyKey } from '../../../api/idempotency';
import { queryKeys } from '../../../api/queryKeys';
import type { QueryAccepted, QueryCreate, SessionListResponse } from '../../../api/types';
import { findActiveExecutionId } from './executionRecovery';

const SELECTED_SESSION_KEY = 'management-star-selected-session';

export function useQuestionWorkspace() {
  const queryClient = useQueryClient();
  const sessionsQuery = useQuery({ queryKey: queryKeys.sessions, queryFn: api.listSessions });
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>(() => sessionStorage.getItem(SELECTED_SESSION_KEY) ?? undefined);
  const [activeExecutionId, setActiveExecutionId] = useState<string>();
  const activateAcceptedQuery = useCallback((accepted: QueryAccepted) => {
    sessionStorage.setItem(SELECTED_SESSION_KEY, accepted.sessionId);
    setSelectedSessionId(accepted.sessionId);
    setActiveExecutionId(accepted.executionId);
    void queryClient.invalidateQueries({ queryKey: queryKeys.messages(accepted.sessionId) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
  }, [queryClient]);

  useEffect(() => {
    const sessions = sessionsQuery.data?.items;
    if (!sessions?.length) return;
    if (selectedSessionId && sessions.some((session) => session.id === selectedSessionId)) return;
    const fallback = sessions.at(0);
    if (!fallback) return;
    const fallbackId = fallback.id;
    sessionStorage.setItem(SELECTED_SESSION_KEY, fallbackId);
    setSelectedSessionId(fallbackId);
  }, [selectedSessionId, sessionsQuery.data]);

  const messagesQuery = useQuery({
    queryKey: queryKeys.messages(selectedSessionId ?? 'none'),
    queryFn: () => api.listMessages(selectedSessionId ?? ''),
    enabled: Boolean(selectedSessionId),
  });

  useEffect(() => {
    if (activeExecutionId || !messagesQuery.data) return;
    setActiveExecutionId(findActiveExecutionId(messagesQuery.data.items));
  }, [activeExecutionId, messagesQuery.data]);

  const executionQuery = useQuery({
    queryKey: queryKeys.execution(activeExecutionId ?? 'none'),
    queryFn: () => api.getExecution(activeExecutionId ?? ''),
    enabled: Boolean(activeExecutionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'queued' || status === 'running' ? 1000 : false;
    },
  });

  useEffect(() => {
    if (!executionQuery.data || !activeExecutionId) return;
    if (['completed', 'failed', 'cancelled', 'rejected'].includes(executionQuery.data.status)) {
      void queryClient.invalidateQueries({ queryKey: queryKeys.messages(executionQuery.data.sessionId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    }
  }, [activeExecutionId, executionQuery.data, queryClient]);

  const createSession = useMutation({
    mutationFn: () => api.createSession(),
    onSuccess: (session) => {
      queryClient.setQueryData<SessionListResponse>(queryKeys.sessions, (current) => current ? {
        ...current,
        items: [session, ...current.items.filter((item) => item.id !== session.id)],
        page: { ...current.page, total: current.page.total + 1 },
      } : current);
      sessionStorage.setItem(SELECTED_SESSION_KEY, session.id);
      setSelectedSessionId(session.id);
      setActiveExecutionId(undefined);
      void queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });

  const updateSession = useMutation({
    mutationFn: ({ id, title, pinned }: { id: string; title?: string; pinned?: boolean }) => api.updateSession(id, { title, pinned }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.sessions }),
  });

  const deleteSession = useMutation({
    mutationFn: api.deleteSession,
    onSuccess: (_, id) => {
      const remaining = sessionsQuery.data?.items.filter((session) => session.id !== id) ?? [];
      if (selectedSessionId === id) {
        const nextId = remaining[0]?.id;
        if (nextId) sessionStorage.setItem(SELECTED_SESSION_KEY, nextId);
        else sessionStorage.removeItem(SELECTED_SESSION_KEY);
        setSelectedSessionId(nextId);
      }
      setActiveExecutionId(undefined);
      void queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });

  const submitQuery = useMutation({
    mutationFn: async ({ question, dataSourceIds }: Pick<QueryCreate, 'question' | 'dataSourceIds'>) => {
      let sessionId = selectedSessionId;
      if (!sessionId) {
        const session = await api.createSession({ title: question.slice(0, 60) });
        sessionId = session.id;
        setSelectedSessionId(session.id);
      }
      return api.createQuery(sessionId, { question, dataSourceIds, generateChart: true });
    },
    onSuccess: activateAcceptedQuery,
  });

  const submitClarification = useMutation({
    mutationFn: async (content: string) => {
      const execution = executionQuery.data;
      if (!execution || execution.status !== 'awaiting_input') throw new Error('当前没有等待补充的问数');
      const round = execution.clarification?.round ?? execution.clarificationRound;
      const idempotencyKey = createClarificationIdempotencyKey(execution.id, round, content);
      return api.submitClarification(execution.id, { content }, idempotencyKey);
    },
    onSuccess: async (accepted) => {
      activateAcceptedQuery(accepted);
      await executionQuery.refetch();
    },
  });

  const resubmitMessage = useMutation({
    mutationFn: ({ messageId, question, dataSourceIds }: { messageId: string; question: string; dataSourceIds: string[] }) =>
      api.resubmitMessage(messageId, { question, dataSourceIds, generateChart: true, contextMessageIds: [] }),
    onSuccess: activateAcceptedQuery,
  });

  const regenerateAnswer = useMutation({
    mutationFn: (messageId: string) => api.regenerateAnswer(messageId, { generateChart: true }),
    onSuccess: activateAcceptedQuery,
  });

  const stopExecution = useMutation({
    mutationFn: () => api.cancelExecution(activeExecutionId ?? ''),
    onSuccess: () => void executionQuery.refetch(),
  });

  const awaitingClarification = executionQuery.data?.status === 'awaiting_input';
  const running = submitQuery.isPending || submitClarification.isPending || resubmitMessage.isPending || regenerateAnswer.isPending || executionQuery.isFetching && !executionQuery.data ||
    executionQuery.data?.status === 'queued' || executionQuery.data?.status === 'running';
  const interactionDisabled = running || awaitingClarification;

  return {
    sessionsQuery,
    sessions: sessionsQuery.data?.items ?? [],
    selectedSessionId,
    setSelectedSessionId: (id?: string) => {
      if (id) sessionStorage.setItem(SELECTED_SESSION_KEY, id);
      else sessionStorage.removeItem(SELECTED_SESSION_KEY);
      setSelectedSessionId(id);
      setActiveExecutionId(undefined);
    },
    messagesQuery,
    activeExecution: executionQuery.data,
    activeExecutionId,
    executionError: executionQuery.error ?? submitQuery.error,
    running,
    createSession,
    updateSession,
    deleteSession,
    submitQuery,
    submitClarification,
    resubmitMessage,
    regenerateAnswer,
    stopExecution,
    awaitingClarification,
    interactionDisabled,
    currentSession: useMemo(() => sessionsQuery.data?.items.find((session) => session.id === selectedSessionId), [sessionsQuery.data, selectedSessionId]),
  };
}
