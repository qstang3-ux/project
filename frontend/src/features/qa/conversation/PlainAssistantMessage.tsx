import { RobotOutlined } from '@ant-design/icons';
import { Space } from 'antd';
import type { Message } from '../../../api/types';
import { CopyButton } from '../../../components/CopyButton';
import { SpeechPlaybackButton } from '../speech/SpeechPlaybackButton';

export function PlainAssistantMessage({ message, speechEnabled }: { message: Message; speechEnabled: boolean }) {
  return (
    <div className="assistant-card assistant-plain">
      <div className="assistant-header">
        <span className="assistant-avatar"><RobotOutlined /></span>
        <div><strong>经管之星</strong><span>历史回答</span></div>
      </div>
      <div className="plain-answer">{message.content}</div>
      <div className="answer-footer">
        <Space size={4}>
          <CopyButton text={message.content} label="复制回答" />
          <SpeechPlaybackButton text={message.content} enabled={speechEnabled} />
        </Space>
        <span>{new Date(message.createdAt).toLocaleString('zh-CN')}</span>
      </div>
    </div>
  );
}
