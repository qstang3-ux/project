import { lazy, Suspense, useEffect, useState } from 'react';
import { Skeleton } from 'antd';
import type { ExecutionDetail } from '../../../api/types';
import { ExecutionSteps } from './ExecutionSteps';
import { ResultTable } from './ResultTable';
import { SqlViewer } from './SqlViewer';
import { TypewriterText } from './TypewriterText';
import { AnswerHighlights } from './AnswerHighlights';
import { AnswerEvidence } from './AnswerEvidence';

const ResultChart = lazy(() => import('./ResultChart').then((module) => ({ default: module.ResultChart })));

export function AnswerContent({ execution, animateAnswer = false }: { execution: ExecutionDetail; animateAnswer?: boolean }) {
  const [highlightedRowIndex, setHighlightedRowIndex] = useState<number | null>(null);
  const isChat = execution.intent === 'chat';
  useEffect(() => setHighlightedRowIndex(null), [execution.id]);
  const validationStep = execution.steps.find((step) => step.type === 'sql_validation');
  const reportedStatus: unknown = execution.sqlValidationStatus;
  const validationStatus = reportedStatus === 'passed' || reportedStatus === 'rejected' || reportedStatus === 'not_started'
    ? reportedStatus
    : validationStep?.status === 'completed' ? 'passed' : validationStep?.status === 'failed' ? 'rejected' : 'not_started';

  return (
    <>
      {!isChat ? <ExecutionSteps execution={execution} /> : null}
      {execution.result ? <AnswerHighlights result={execution.result} /> : null}
      {!isChat ? <AnswerEvidence execution={execution} /> : null}
      {execution.sql ? <SqlViewer sql={execution.sql} validationStatus={validationStatus} /> : null}
      {execution.result ? <ResultTable result={execution.result} highlightedRowIndex={highlightedRowIndex} onHighlightRow={setHighlightedRowIndex} /> : null}
      {execution.chart && execution.result ? (
        <Suspense fallback={<div className="chart-loading"><Skeleton active paragraph={{ rows: 5 }} /></div>}>
          <ResultChart chart={execution.chart} result={execution.result} highlightedRowIndex={highlightedRowIndex} onHighlightRow={setHighlightedRowIndex} />
        </Suspense>
      ) : null}
      {execution.answer ? <div className="answer-summary"><TypewriterText text={execution.answer} animate={animateAnswer && execution.status === 'completed'} /></div> : null}
      {(execution.status === 'queued' || execution.status === 'running') && !execution.answer ? (
        <div className="answer-loading answer-conclusion-loading" role="status" aria-live="polite">
          <span className="answer-loading-mark" aria-hidden="true"><i /><i /><i /></span>
          <div><strong>{execution.status === 'queued' ? '正在准备分析' : '正在生成回答'}</strong><span>数据处理完成后，回答内容会显示在这里</span></div>
        </div>
      ) : null}
    </>
  );
}
