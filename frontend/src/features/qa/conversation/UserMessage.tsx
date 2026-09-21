import { CloseOutlined, EditOutlined, SendOutlined, UserOutlined } from '@ant-design/icons';
import { Button, Input, Space, Tooltip } from 'antd';
import { useState } from 'react';
import type { Message } from '../../../api/types';
import { CopyButton } from '../../../components/CopyButton';
import { FavoriteQuestionButton } from '../quick-questions/FavoriteQuestionButton';

interface UserMessageProps {
  message: Message;
  disabled?: boolean;
  submitting?: boolean;
  onResubmit?: (message: Message, question: string) => void;
}

export function UserMessage({ message, disabled = false, submitting = false, onResubmit }: UserMessageProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  const cancel = () => {
    setDraft(message.content);
    setEditing(false);
  };
  const submit = () => {
    const question = draft.trim();
    if (!question || question === message.content.trim()) return;
    onResubmit?.(message, question);
  };
  return (
    <div className="user-message">
      <span className="user-avatar"><UserOutlined /></span>
      <div>
        {editing ? (
          <div className="user-message-editor">
            <Input.TextArea aria-label="编辑问题" value={draft} maxLength={2000} autoSize={{ minRows: 2, maxRows: 6 }} onChange={(event) => setDraft(event.target.value)} />
            <Space size={6}>
              <Button size="small" icon={<CloseOutlined />} onClick={cancel}>取消</Button>
              <Button size="small" type="primary" icon={<SendOutlined />} loading={submitting} disabled={disabled || !draft.trim() || draft.trim() === message.content.trim()} onClick={submit}>重新发送</Button>
            </Space>
          </div>
        ) : <p>{message.content}</p>}
        <span className="user-message-meta">{new Date(message.createdAt).toLocaleString('zh-CN')} <FavoriteQuestionButton question={message.content} sourceMessageId={message.id} /> <CopyButton text={message.content} label="复制问题" /> {onResubmit ? <Tooltip title="编辑并创建新分支"><Button className="message-inline-action" type="text" size="small" icon={<EditOutlined />} aria-label="编辑问题" disabled={disabled} onClick={() => setEditing(true)} /></Tooltip> : null}</span>
      </div>
    </div>
  );
}
