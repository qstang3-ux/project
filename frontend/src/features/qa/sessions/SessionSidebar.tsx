import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Empty, Input, Modal, Skeleton, Tooltip, Typography } from 'antd';
import { useState } from 'react';
import type { Session } from '../../../api/types';
import { SessionListItem } from './SessionListItem';

interface SessionSidebarProps {
  sessions: Session[];
  selectedId?: string;
  loading: boolean;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onUpdate: (id: string, values: { title?: string; pinned?: boolean }) => void;
  onDelete: (id: string) => void;
}

export function SessionSidebar({ sessions, selectedId, loading, onSelect, onCreate, onUpdate, onDelete }: SessionSidebarProps) {
  const { modal } = App.useApp();
  const [renameSession, setRenameSession] = useState<Session>();
  const [renameValue, setRenameValue] = useState('');

  return (
    <aside className="session-sidebar" aria-label="会话列表">
      <div className="session-sidebar-header">
        <div><strong>智能问数</strong><span>近 30 天记录</span></div>
        <Tooltip title="开启新对话"><Button className="icon-button icon-button-primary new-session-button" type="text" icon={<PlusOutlined />} onClick={onCreate} aria-label="开启新对话" /></Tooltip>
      </div>
      <div className="session-list">
        {loading ? <Skeleton active paragraph={{ rows: 6 }} /> : null}
        {!loading && sessions.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无会话" /> : null}
        {sessions.map((session) => (
          <SessionListItem
            key={session.id}
            session={session}
            selected={selectedId === session.id}
            onSelect={() => onSelect(session.id)}
            onTogglePinned={() => onUpdate(session.id, { pinned: !session.pinned })}
            onRename={() => { setRenameSession(session); setRenameValue(session.title); }}
            onDelete={() => {
              modal.confirm({ title: '删除会话？', content: '会话及其消息将无法恢复。', okText: '删除', okButtonProps: { danger: true }, cancelText: '取消', onOk: () => onDelete(session.id) });
            }}
          />
        ))}
      </div>
      <Modal
        title="重命名会话"
        open={Boolean(renameSession)}
        okText="保存"
        cancelText="取消"
        okButtonProps={{ disabled: !renameValue.trim() || renameValue.trim().length > 60 }}
        onCancel={() => setRenameSession(undefined)}
        onOk={() => { if (renameSession) onUpdate(renameSession.id, { title: renameValue.trim() }); setRenameSession(undefined); }}
      >
        <Typography.Text>会话名称</Typography.Text>
        <Input value={renameValue} onChange={(event) => setRenameValue(event.target.value)} maxLength={60} showCount autoFocus />
      </Modal>
    </aside>
  );
}
