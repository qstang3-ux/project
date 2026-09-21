import { Alert, Card, Skeleton } from 'antd';
import type { ExecutionDetail } from '../../../api/types';
import { ErrorState } from '../../../components/ErrorState';
import { AnswerActions } from './AnswerActions';
import { AnswerContent } from './AnswerContent';
import { AssistantMessageHeader } from './AssistantMessageHeader';
import { FeedbackModal } from './FeedbackModal';
import { FollowUpQuestions } from './FollowUpQuestions';
import { ClarificationPrompt } from './ClarificationPrompt';
import { useAssistantExecution } from './useAssistantExecution';
import { AnswerVersionsDrawer } from './AnswerVersionsDrawer';

interface AssistantMessageProps {
  executionId: string;
  preview?: ExecutionDetail;
  onFollowUp: (question: string) => void;
  onRegenerate?: (messageId: string) => void;
  regenerating?: boolean;
  speechEnabled: boolean;
  animateAnswer?: boolean;
}

export function AssistantMessage({ executionId, preview, onFollowUp, onRegenerate, regenerating = false, speechEnabled, animateAnswer = false }: AssistantMessageProps) {
  const state = useAssistantExecution(executionId, preview);

  if (state.executionQuery.isLoading) return <Card className="assistant-card"><Skeleton active paragraph={{ rows: 7 }} /></Card>;
  if (state.executionQuery.isError || !state.executionQuery.data) return <Card className="assistant-card"><ErrorState title="回答加载失败" error={state.executionQuery.error} onRetry={() => void state.executionQuery.refetch()} /></Card>;

  const execution = state.executionQuery.data;
  const isFailure = execution.status === 'failed' || execution.status === 'rejected' || execution.status === 'cancelled';
  return (
    <Card className="assistant-card">
      <AssistantMessageHeader status={execution.status} />
      {isFailure ? <Alert type={execution.status === 'cancelled' ? 'info' : 'error'} showIcon message={execution.error?.message ?? statusLabel(execution.status)} description="你可以调整问题或数据源后重新提问。" /> : null}
      {execution.status === 'awaiting_input' ? (
        <ClarificationPrompt
          key={execution.clarification?.round ?? execution.clarificationRound}
          clarification={execution.clarification}
          intent={execution.intent}
          normalizedQuestion={execution.normalizedQuestion}
          missingSlots={execution.missingSlots}
          clarificationRound={execution.clarificationRound}
          submitting={state.clarificationMutation.isPending}
          cancelling={state.cancelMutation.isPending}
          onSubmit={state.submitClarification}
          onCancel={() => state.cancelMutation.mutate()}
        />
      ) : null}
      <AnswerContent execution={execution} animateAnswer={animateAnswer} />
      <AnswerActions execution={execution} speechEnabled={speechEnabled} regenerating={regenerating} onFeedback={() => state.setFeedbackOpen(true)} onRegenerate={onRegenerate ? () => onRegenerate(execution.userMessageId) : undefined} onVersions={() => state.setVersionsOpen(true)} exporting={state.exportMutation.isPending} onExport={() => state.exportMutation.mutate()} />
      <FollowUpQuestions questions={execution.followUpQuestions ?? []} chart={execution.chart} onSelect={onFollowUp} />
      <FeedbackModal open={state.feedbackOpen} submitting={state.feedbackMutation.isPending} onCancel={() => state.setFeedbackOpen(false)} onSubmit={(reason, description) => state.feedbackMutation.mutate({ execution, reason, description })} />
      <AnswerVersionsDrawer messageId={execution.userMessageId} open={state.versionsOpen} onClose={() => state.setVersionsOpen(false)} />
    </Card>
  );
}

function statusLabel(status: string): string {
  return { queued: '排队中', running: '执行中', awaiting_input: '待补充信息', completed: '已完成', failed: '执行失败', cancelled: '已停止', rejected: '安全拒绝' }[status] ?? '未知状态';
}
