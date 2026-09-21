import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate } from '../../api/types';

export type ModelFormValues = ModelConfigCreate;

export const emptyModelForm: ModelFormValues = {
  name: '',
  provider: 'openai_compatible',
  protocol: 'responses',
  baseUrl: '',
  modelName: '',
  apiKey: '',
  timeoutSeconds: 30,
  enabled: true,
};

export function modelToForm(model: ModelConfig): ModelFormValues {
  return {
    name: model.name,
    provider: model.provider,
    protocol: model.protocol,
    baseUrl: model.baseUrl,
    modelName: model.modelName,
    apiKey: '',
    timeoutSeconds: model.timeoutSeconds,
    enabled: model.enabled,
  };
}

export function modelFormToUpdate(values: ModelFormValues): ModelConfigUpdate {
  return {
    name: values.name,
    protocol: values.protocol,
    baseUrl: values.baseUrl,
    modelName: values.modelName,
    timeoutSeconds: values.timeoutSeconds,
    enabled: values.enabled,
    ...(values.apiKey ? { apiKey: values.apiKey } : {}),
  };
}
