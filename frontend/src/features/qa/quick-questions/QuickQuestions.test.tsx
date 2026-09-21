import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from 'antd';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QuickQuestions } from './QuickQuestions';

const apiMocks = vi.hoisted(() => ({
  listFrequentQuestions: vi.fn().mockResolvedValue([{ question: '查询月度收入趋势', count: 6, lastAskedAt: '2026-09-17T00:00:00Z' }]),
  listFavorites: vi.fn().mockResolvedValue([]),
  removeFavorite: vi.fn(),
}));

vi.mock('../../../api/client', () => ({ api: apiMocks }));

describe('QuickQuestions', () => {
  it('loads frequent questions, fills the editor, and closes the panel', async () => {
    const onSelect = vi.fn();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<App><QueryClientProvider client={queryClient}><QuickQuestions frequentEnabled onSelect={onSelect} /></QueryClientProvider></App>);

    fireEvent.click(screen.getByRole('button', { name: '打开快捷提问' }));
    const question = await screen.findByRole('button', { name: /查询月度收入趋势/ });
    fireEvent.click(question);

    expect(onSelect).toHaveBeenCalledWith('查询月度收入趋势');
    await waitFor(() => expect(screen.queryByRole('button', { name: /查询月度收入趋势/ })).not.toBeInTheDocument());
  }, 10_000);
});
