import { ArrowUpOutlined, AudioOutlined } from '@ant-design/icons';
import { App, Button, Input, Tooltip } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { DataSourcePicker } from './DataSourcePicker';
import type { DataSource } from '../../../api/types';
import { useBrowserSpeechRecognition } from '../speech/useBrowserSpeechRecognition';
import { QuickQuestions } from '../quick-questions/QuickQuestions';

interface QuestionComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  running: boolean;
  sources: DataSource[];
  selectedSourceIds: string[];
  maxSelection: number;
  sourcesLoading: boolean;
  sourcesError: boolean;
  onSourcesChange: (ids: string[]) => void;
  speechEnabled?: boolean;
  frequentQuestionsEnabled?: boolean;
  onQuickQuestionSelect: (question: string) => void;
}

export function QuestionComposer(props: QuestionComposerProps) {
  const { message } = App.useApp();
  const [composing, setComposing] = useState(false);
  const submitLockedRef = useRef(false);
  const tooLong = props.value.length > 2000;
  const disabled = !props.value.trim() || tooLong || props.selectedSourceIds.length === 0 || props.running;
  const speech = useBrowserSpeechRecognition({
    enabled: Boolean(props.speechEnabled) && !props.running,
    value: props.value,
    onChange: props.onChange,
    onError: (errorMessage) => void message.warning(errorMessage),
  });

  useEffect(() => {
    if (!props.running) submitLockedRef.current = false;
  }, [props.running]);

  const submit = () => {
    if (disabled || submitLockedRef.current) return;
    submitLockedRef.current = true;
    props.onSubmit();
  };

  return (
    <div className="composer-wrap">
      <div className="composer">
        <Input.TextArea
          aria-label="问题输入"
          placeholder="请输入经营数据问题，Enter 发送，Shift+Enter 换行"
          autoSize={{ minRows: 1, maxRows: 5 }}
          value={props.value}
          onChange={(event) => props.onChange(event.target.value)}
          onCompositionStart={() => setComposing(true)}
          onCompositionEnd={() => setComposing(false)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && !composing) {
              event.preventDefault();
              submit();
            }
          }}
          status={tooLong ? 'error' : undefined}
        />
        <div className="composer-footer">
          <div className="composer-context-tools">
            <QuickQuestions frequentEnabled={props.frequentQuestionsEnabled !== false} onSelect={props.onQuickQuestionSelect} />
            <DataSourcePicker sources={props.sources} selectedIds={props.selectedSourceIds} maxSelection={props.maxSelection} loading={props.sourcesLoading} error={props.sourcesError} onChange={props.onSourcesChange} />
            <span className={`composer-count ${tooLong ? 'count-error' : ''}`}>{props.value.length}/2000</span>
          </div>
          <div className="composer-actions">
            {props.speechEnabled ? (
              <Tooltip title={speech.supported ? (speech.listening ? '停止语音输入' : '语音输入') : '当前浏览器不支持语音输入'}>
                <span>
                  <Button
                    className={`speech-input-button${speech.listening ? ' is-listening' : ''}`}
                    aria-label={speech.listening ? '停止语音输入' : '开始语音输入'}
                    aria-pressed={speech.listening}
                    danger={speech.listening}
                    icon={<AudioOutlined />}
                    disabled={!speech.supported || props.running}
                    onClick={speech.listening ? speech.stop : speech.start}
                  />
                </span>
              </Tooltip>
            ) : null}
            {props.running ? (
              <Tooltip title="正在生成，点击停止">
                <Button className="send-running-button" shape="circle" aria-label="停止当前问数" onClick={props.onStop}>
                  <span className="send-running-indicator" aria-hidden="true"><i /></span>
                </Button>
              </Tooltip>
            ) : (
              <Tooltip title={props.selectedSourceIds.length === 0 ? '请先选择数据源' : '发送问题'}>
                <span>
                  <Button
                    className="send-question-button"
                    type="primary"
                    shape="circle"
                    icon={<ArrowUpOutlined />}
                    aria-label="发送问题"
                    disabled={disabled}
                    onClick={submit}
                  />
                </span>
              </Tooltip>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
