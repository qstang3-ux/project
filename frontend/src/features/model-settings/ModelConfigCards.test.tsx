import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ModelConfig } from '../../api/types';
import { ModelConfigCards } from './ModelConfigCards';

const model: ModelConfig = {
  id: '77777777-7777-4777-8777-777777777777',
  name: '经营分析模型',
  provider: 'openai_compatible',
  protocol: 'chat_completions',
  baseUrl: 'https://api.example.com/v1',
  modelName: 'business-analyst-v1',
  apiKeyMask: 'sk-****demo',
  timeoutSeconds: 30,
  enabled: true,
  isActive: true,
  lastTestStatus: 'success',
  lastTestedAt: '2026-09-17T01:00:00.000Z',
  createdAt: '2026-09-17T01:00:00.000Z',
  updatedAt: '2026-09-17T01:30:00.000Z',
};

describe('ModelConfigCards', () => {
  it('renders demo-style scene selection without exposing the API key mask', () => {
    render(<ModelConfigCards models={[model]} loading={false} activating={false} onAdd={vi.fn()} onEdit={vi.fn()} onActivate={vi.fn()} onDelete={vi.fn()} />);

    expect(screen.getByRole('region', { name: '智能问数模型配置' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: '模型 经营分析模型' })).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByText('Chat Completions')).toBeInTheDocument();
    expect(screen.getByText('https://api.example.com/v1')).toHaveAttribute('title', 'https://api.example.com/v1');
    expect(screen.queryByText('sk-****demo')).not.toBeInTheDocument();
    expect(screen.queryByText('API Key')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑当前模型' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '编辑模型 经营分析模型' })).toBeEnabled();
  });
});
