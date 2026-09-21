import { DeleteOutlined, EditOutlined, MoreOutlined, PushpinFilled, PushpinOutlined } from '@ant-design/icons';
import { Button, Dropdown } from 'antd';
import type { Session } from '../../../api/types';

interface SessionListItemProps {
  session: Session;
  selected: boolean;
  onSelect: () => void;
  onTogglePinned: () => void;
  onRename: () => void;
  onDelete: () => void;
}

export function SessionListItem({ session, selected, onSelect, onTogglePinned, onRename, onDelete }: SessionListItemProps) {
  return (
    <div className={`session-item ${selected ? 'active' : ''}`}>
      <button type="button" className="session-item-main" onClick={onSelect} aria-current={selected ? 'true' : undefined} aria-label={`打开会话：${session.title}`}>
        <span className="session-title">{session.pinned ? <PushpinFilled /> : null}{session.title}</span>
        <span className="session-preview">{session.lastMessagePreview ?? '尚未开始提问'}</span>
      </button>
      <Dropdown
        trigger={['click']}
        menu={{
          items: [
            { key: 'pin', icon: session.pinned ? <PushpinOutlined /> : <PushpinFilled />, label: session.pinned ? '取消置顶' : '置顶' },
            { key: 'rename', icon: <EditOutlined />, label: '重命名' },
            { key: 'delete', icon: <DeleteOutlined />, danger: true, label: '删除' },
          ],
          onClick: ({ key }) => {
            if (key === 'pin') onTogglePinned();
            if (key === 'rename') onRename();
            if (key === 'delete') onDelete();
          },
        }}
      >
        <Button className="icon-button icon-button-quiet" type="text" size="small" icon={<MoreOutlined />} aria-label={`${session.title} 更多操作`} />
      </Dropdown>
    </div>
  );
}
