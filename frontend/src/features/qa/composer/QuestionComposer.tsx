import { ArrowUpOutlined, AudioOutlined, QuestionCircleOutlined, StopOutlined } from '@ant-design/icons';
import { App, Button, Input, Popconfirm, Tooltip } from 'antd';
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
  clarificationMode?: boolean;
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
  const clarificationMode = props.clarificationMode === true;
  const disabled = !props.value.trim() || tooLong || !clarificationMode && props.selectedSourceIds.length === 0 || props.running;
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
          aria-label={clarificationMode ? '补充信息' : '问题输入'}
          placeholder={clarificationMode ? '请在这里补充时间范围、经营单元或指标口径' : '请输入经营数据问题，Enter 发送，Shift+Enter 换行'}
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
            {clarificationMode ? (
              <div className="clarification-composer-context">
                <QuestionCircleOutlined />
                <span>补充当前问题</span>
              </div>
            ) : (
              <>
                <QuickQuestions frequentEnabled={props.frequentQuestionsEnabled !== false} onSelect={props.onQuickQuestionSelect} />
                <DataSourcePicker sources={props.sources} selectedIds={props.selectedSourceIds} maxSelection={props.maxSelection} loading={props.sourcesLoading} error={props.sourcesError} onChange={props.onSourcesChange} />
              </>
            )}
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
              <>
                {clarificationMode ? (
                  <Popconfirm title="停止本次问数？" description="当前补充内容不会继续执行。" okText="停止" cancelText="继续填写" okButtonProps={{ danger: true }} onConfirm={props.onStop}>
                    <Button className="clarification-stop-button" icon={<StopOutlined />} aria-label="停止">停止</Button>
                  </Popconfirm>
                ) : null}
                <Tooltip title={clarificationMode ? '提交补充信息' : props.selectedSourceIds.length === 0 ? '请先选择数据源' : '发送问题'}>
                  <span>
                    <Button
                      className="send-question-button"
                      type="primary"
                      shape="circle"
                      icon={<ArrowUpOutlined />}
                      aria-label={clarificationMode ? '提交并继续' : '发送问题'}
                      disabled={disabled}
                      onClick={submit}
                    />
                  </span>
                </Tooltip>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
