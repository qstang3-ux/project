import { DownloadOutlined, ExclamationCircleOutlined, HistoryOutlined, RedoOutlined } from '@ant-design/icons';
import { Button, Space, Tooltip } from 'antd';
import type { ExecutionDetail } from '../../../api/types';
import { CopyButton } from '../../../components/CopyButton';
import { SpeechPlaybackButton } from '../speech/SpeechPlaybackButton';

interface AnswerActionsProps {
  execution: ExecutionDetail;
  onFeedback: () => void;
  speechEnabled: boolean;
  regenerating?: boolean;
  onRegenerate?: () => void;
  onVersions: () => void;
  exporting?: boolean;
  onExport?: () => void;
}

export function AnswerActions({ execution, onFeedback, speechEnabled, regenerating = false, onRegenerate, onVersions, exporting = false, onExport }: AnswerActionsProps) {
  const tokenUsage = execution.tokenUsage;
  const metadata = [
    execution.durationMs !== null && execution.durationMs !== undefined ? `耗时 ${(execution.durationMs / 1000).toFixed(1)}s` : null,
    `Token ${tokenUsage.totalTokens.toLocaleString('zh-CN')}`,
    execution.modelName,
  ].filter((item): item is string => Boolean(item));
  return (
    <div className="answer-footer">
      <Space>
        {execution.answer ? <CopyButton text={execution.answer} label="复制回答" /> : null}
        {execution.answer ? <SpeechPlaybackButton text={execution.answer} enabled={speechEnabled} /> : null}
        {execution.status === 'completed' && onRegenerate ? <Tooltip title="重新生成回答"><Button className="answer-action icon-button icon-button-quiet" type="text" size="small" icon={<RedoOutlined />} aria-label="重新生成回答" loading={regenerating} onClick={onRegenerate} /></Tooltip> : null}
        {execution.status === 'completed' ? <Tooltip title="查看回答版本"><Button className="answer-action icon-button icon-button-quiet" type="text" size="small" icon={<HistoryOutlined />} aria-label="查看回答版本" onClick={onVersions} /></Tooltip> : null}
        {execution.status === 'completed' && execution.result?.rows.length && onExport ? <Tooltip title="导出 CSV"><Button className="answer-action icon-button icon-button-quiet" type="text" size="small" icon={<DownloadOutlined />} aria-label="导出 CSV" loading={exporting} onClick={onExport} /></Tooltip> : null}
        {execution.assistantMessageId ? (
          <Tooltip title="数据有误">
            <Button
              className="answer-action icon-button icon-button-quiet"
              type="text"
              size="small"
              icon={<ExclamationCircleOutlined />}
              aria-label="数据有误"
              onClick={onFeedback}
            />
          </Tooltip>
        ) : null}
      </Space>
      <Tooltip title={`输入 ${tokenUsage.promptTokens.toLocaleString('zh-CN')} / 输出 ${tokenUsage.completionTokens.toLocaleString('zh-CN')} / 总计 ${tokenUsage.totalTokens.toLocaleString('zh-CN')}`}>
        <span className="answer-metadata">{metadata.join(' · ')}</span>
      </Tooltip>
    </div>
  );
}
