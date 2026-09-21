import { ArrowDownOutlined } from '@ant-design/icons';
import { Alert, App, Button, Spin, Tooltip } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api } from '../../../api/client';
import { getErrorMessage } from '../../../api/errorMessages';
import { queryKeys } from '../../../api/queryKeys';
import { ErrorState } from '../../../components/ErrorState';
import { QuestionComposer } from '../composer/QuestionComposer';
import { MessageList } from '../conversation/MessageList';
import { WelcomePanel } from '../conversation/WelcomePanel';
import { SessionSidebar } from '../sessions/SessionSidebar';
import { QuestionWorkspaceHeader } from './QuestionWorkspaceHeader';
import { useConversationScroll } from './useConversationScroll';
import { useQuestionWorkspace } from './useQuestionWorkspace';

export function QuestionWorkspace() {
  const { message } = App.useApp();
  const workspace = useQuestionWorkspace();
  const configQuery = useQuery({ queryKey: queryKeys.applicationConfig, queryFn: api.getApplicationConfig });
  const sourcesQuery = useQuery({ queryKey: queryKeys.dataSources, queryFn: api.listDataSources });
  const [question, setQuestion] = useState('');
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const messages = workspace.messagesQuery.data?.items ?? [];
  const conversation = useConversationScroll({
    sessionId: workspace.selectedSessionId,
    messageCount: messages.length,
    executionId: workspace.activeExecutionId,
    executionStatus: workspace.activeExecution?.status,
  });

  useEffect(() => {
    if (!selectedSourceIds.length && sourcesQuery.data) {
      setSelectedSourceIds(sourcesQuery.data.items.filter((source) => source.enabled && source.isDefault).map((source) => source.id));
    }
  }, [selectedSourceIds.length, sourcesQuery.data]);

  const submit = () => {
    const trimmed = question.trim();
    if (!trimmed || !selectedSourceIds.length) return;
    conversation.markForAutoScroll();
    workspace.submitQuery.mutate({ question: trimmed, dataSourceIds: selectedSourceIds }, {
      onSuccess: () => setQuestion(''),
      onError: (error) => void message.error(getErrorMessage(error)),
    });
  };

  if (workspace.sessionsQuery.isLoading || configQuery.isLoading) {
    return <div className="async-state" role="status"><Spin size="large" /><span>加载智能问数工作区...</span></div>;
  }
  if (workspace.sessionsQuery.isError || configQuery.isError || !configQuery.data) {
    return <ErrorState title="智能问数加载失败" error={workspace.sessionsQuery.error ?? configQuery.error} primaryAction onRetry={() => { void workspace.sessionsQuery.refetch(); void configQuery.refetch(); }} />;
  }

  const showWelcome = !workspace.selectedSessionId || messages.length === 0 && !workspace.activeExecutionId;
  return (
    <div className="qa-page">
      <SessionSidebar
        sessions={workspace.sessions}
        selectedId={workspace.selectedSessionId}
        loading={workspace.sessionsQuery.isLoading}
        onSelect={workspace.setSelectedSessionId}
        onCreate={() => workspace.createSession.mutate()}
        onUpdate={(id, values) => workspace.updateSession.mutate({ id, ...values })}
        onDelete={(id) => workspace.deleteSession.mutate(id)}
      />
      <main className="qa-workspace">
        <QuestionWorkspaceHeader title={workspace.currentSession?.title ?? '新建分析'} selectedSourceCount={selectedSourceIds.length} />
        <div className="qa-scroll" ref={conversation.conversationRef} {...conversation.scrollHandlers}>
          {showWelcome ? (
            <WelcomePanel config={configQuery.data} onSelect={setQuestion} />
          ) : (
            <MessageList
              messages={messages}
              loading={workspace.messagesQuery.isLoading}
              activeExecution={workspace.activeExecution}
              activeExecutionId={workspace.activeExecutionId}
              onFollowUp={setQuestion}
              onResubmit={(source, editedQuestion) => workspace.resubmitMessage.mutate({ messageId: source.id, question: editedQuestion, dataSourceIds: selectedSourceIds }, { onSuccess: () => void message.success('已创建编辑分支，正在重新分析。'), onError: (error) => void message.error(getErrorMessage(error)) })}
              resubmitting={workspace.resubmitMessage.isPending}
              interactionDisabled={workspace.running}
              onRegenerate={(messageId) => workspace.regenerateAnswer.mutate(messageId, { onSuccess: () => void message.success('正在重新生成回答。'), onError: (error) => void message.error(getErrorMessage(error)) })}
              regenerating={workspace.regenerateAnswer.isPending}
              speechEnabled={configQuery.data.ttsEnabled}
            />
          )}
          {workspace.executionError ? <Alert className="qa-error" type="error" showIcon closable message="问数请求失败" description={getErrorMessage(workspace.executionError)} /> : null}
        </div>
        {conversation.showScrollToBottom ? <Tooltip title="回到最新消息"><Button className="scroll-to-bottom" shape="circle" icon={<ArrowDownOutlined />} onClick={() => conversation.scrollToBottom()} aria-label="回到底部" /></Tooltip> : null}
        <QuestionComposer
          value={question}
          onChange={setQuestion}
          onSubmit={submit}
          onStop={() => workspace.stopExecution.mutate()}
          running={workspace.running}
          sources={sourcesQuery.data?.items ?? []}
          selectedSourceIds={selectedSourceIds}
          maxSelection={sourcesQuery.data?.maxSelection ?? 8}
          sourcesLoading={sourcesQuery.isLoading}
          sourcesError={sourcesQuery.isError}
          onSourcesChange={setSelectedSourceIds}
          speechEnabled={configQuery.data.sttEnabled}
          frequentQuestionsEnabled={configQuery.data.frequentQuestionsEnabled}
          onQuickQuestionSelect={setQuestion}
        />
      </main>
    </div>
  );
}
