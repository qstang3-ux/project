import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SessionSidebar } from './SessionSidebar';

const session = {
  id: 'session-1',
  title: '季度趋势',
  pinned: false,
  messageCount: 1,
  lastMessagePreview: '查看最近三个季度',
  createdAt: '2026-09-16T00:00:00Z',
  updatedAt: '2026-09-16T00:00:00Z',
};

describe('SessionSidebar', () => {
  it('keeps session selection keyboard accessible without nesting buttons', () => {
    const onSelect = vi.fn();
    const { container } = render(
      <SessionSidebar
        sessions={[session]}
        selectedId={session.id}
        loading={false}
        onSelect={onSelect}
        onCreate={vi.fn()}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    const sessionButton = screen.getByRole('button', { name: '打开会话：季度趋势' });
    expect(sessionButton.tagName).toBe('BUTTON');
    expect(container.querySelector('[role="button"] button')).toBeNull();

    fireEvent.click(sessionButton);
    expect(onSelect).toHaveBeenCalledWith(session.id);
  });
});
