import { Empty } from 'antd';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<div><strong>{title}</strong>{description ? <span>{description}</span> : null}</div>} />
      {action}
    </div>
  );
}
