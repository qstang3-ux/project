import { describe, expect, it } from 'vitest';
import { modelFormToUpdate, modelToForm } from './modelForm';

describe('model form mapping', () => {
  it('keeps protocol and never sends an empty API key during edit', () => {
    const form = modelToForm({
      id: 'model-1',
      name: '经营模型',
      provider: 'openai_compatible',
      protocol: 'responses',
      baseUrl: 'https://api.example.com/v1',
      modelName: 'analysis-v1',
      apiKeyMask: '****demo',
      timeoutSeconds: 30,
      enabled: true,
      isActive: false,
      createdAt: '2026-09-16T00:00:00Z',
      updatedAt: '2026-09-16T00:00:00Z',
    });

    expect(form.protocol).toBe('responses');
    expect(modelFormToUpdate(form)).not.toHaveProperty('apiKey');
  });
});
