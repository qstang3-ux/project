import { Form } from 'antd';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ModelConfig } from '../../api/types';
import { ModelConfigDialog } from './ModelConfigDialog';
import { modelToForm, type ModelFormValues } from './modelForm';

const model: ModelConfig = {
  id: '77777777-7777-4777-8777-777777777777',
  name: '经营分析模型',
  provider: 'openai_compatible',
  protocol: 'responses',
  baseUrl: 'https://api.example.com/v1',
  modelName: 'business-analyst-v1',
  apiKeyMask: 'sk-****demo',
  timeoutSeconds: 30,
  enabled: true,
  isActive: true,
  createdAt: '2026-09-17T01:00:00.000Z',
  updatedAt: '2026-09-17T01:30:00.000Z',
};

function EditingDialog() {
  const [form] = Form.useForm<ModelFormValues>();
  return (
    <ModelConfigDialog
      open
      editing={model}
      form={form}
      saving={false}
      testing={false}
      testFailed={false}
      onCancel={vi.fn()}
      onSave={vi.fn()}
      onTest={vi.fn()}
    />
  );
}

describe('ModelConfigDialog', () => {
  it('never reveals a stored secret and requires an explicit replacement action', () => {
    render(<EditingDialog />);
    const form = screen.getByRole('dialog', { name: '编辑模型' });

    expect(form).toHaveTextContent('API Key 已安全保存');
    expect(form).not.toHaveTextContent(model.apiKeyMask);
    expect(screen.queryByLabelText('新的 API Key')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '更换 API Key' }));
    const input = screen.getByLabelText('新的 API Key');
    expect(input).toHaveAttribute('type', 'password');
    expect(input).toHaveValue('');
    expect(modelToForm(model).apiKey).toBe('');
  }, 15_000);
});
