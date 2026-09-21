import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { TypewriterText } from './TypewriterText';

describe('TypewriterText', () => {
  afterEach(() => vi.useRealTimers());

  it('reveals a new answer progressively and finishes with the complete text', async () => {
    vi.useFakeTimers();
    render(<TypewriterText text="这是一条逐字出现的新回答" animate />);

    const paragraph = screen.getByLabelText('这是一条逐字出现的新回答');
    expect(paragraph).not.toHaveTextContent('这是一条逐字出现的新回答');
    await act(() => vi.advanceTimersByTime(24));
    expect(paragraph.textContent.length).toBeGreaterThan(0);
    await act(() => vi.advanceTimersByTime(5000));
    expect(screen.getByLabelText('这是一条逐字出现的新回答')).toHaveTextContent('这是一条逐字出现的新回答');
  });

  it('shows historical answers immediately', () => {
    render(<TypewriterText text="历史回答直接显示" animate={false} />);
    expect(screen.getByText('历史回答直接显示')).toBeInTheDocument();
  });

  it('renders safe GitHub-flavored Markdown after typing completes', () => {
    const { container } = render(<TypewriterText text={'**重点**\n\n- 收入\n- 回款\n\n`只读 SQL`\n\n<script>alert(1)</script>'} animate={false} />);

    expect(screen.getByText('重点').tagName).toBe('STRONG');
    expect(screen.getByText('收入').closest('li')).not.toBeNull();
    expect(screen.getByText('只读 SQL').tagName).toBe('CODE');
    expect(container.querySelector('script')).toBeNull();
    expect(screen.queryByText('alert(1)')).not.toBeInTheDocument();
  });
});
