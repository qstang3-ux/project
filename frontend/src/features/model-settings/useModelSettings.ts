import { App, Form } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../api/client';
import { getErrorMessage } from '../../api/errorMessages';
import { queryKeys } from '../../api/queryKeys';
import type { ModelConfig } from '../../api/types';
import { emptyModelForm, modelFormToUpdate, modelToForm, type ModelFormValues } from './modelForm';

export function useModelSettings() {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<ModelFormValues>();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ModelConfig>();
  const [testResult, setTestResult] = useState<string>();
  const modelsQuery = useQuery({ queryKey: queryKeys.models, queryFn: api.listModels });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.models });

  const saveMutation = useMutation({
    mutationFn: (values: ModelFormValues) => editing ? api.updateModel(editing.id, modelFormToUpdate(values)) : api.createModel(values),
    onSuccess: () => {
      setOpen(false);
      form.resetFields();
      refresh();
      void message.success(editing ? '模型配置已更新' : '模型配置已创建');
    },
    onError: (error) => void message.error(getErrorMessage(error)),
  });
  const testMutation = useMutation({
    mutationFn: (values: ModelFormValues) => api.testModel(editing && !values.apiKey ? { modelConfigId: editing.id } : values),
    onSuccess: (result) => setTestResult(`${result.message}（${String(result.durationMs)}ms）`),
    onError: (error) => setTestResult(getErrorMessage(error)),
  });
  const activateMutation = useMutation({
    mutationFn: api.activateModel,
    onSuccess: () => { refresh(); void message.success('已切换当前模型'); },
    onError: (error) => void message.error(getErrorMessage(error)),
  });
  const deleteMutation = useMutation({
    mutationFn: api.deleteModel,
    onSuccess: () => { refresh(); void message.success('模型已删除'); },
    onError: (error) => void message.error(getErrorMessage(error)),
  });

  const openEditor = (model?: ModelConfig) => {
    setEditing(model);
    setTestResult(undefined);
    setOpen(true);
    form.setFieldsValue(model ? modelToForm(model) : emptyModelForm);
  };

  const closeEditor = () => {
    if (saveMutation.isPending || testMutation.isPending) return;
    if (!form.isFieldsTouched()) {
      setOpen(false);
      return;
    }
    modal.confirm({
      title: '放弃未保存的模型配置？',
      zIndex: 1300,
      content: '关闭后，本次填写的内容不会保留。',
      okText: '放弃修改',
      okButtonProps: { danger: true },
      cancelText: '继续编辑',
      onOk: () => { setOpen(false); form.resetFields(); },
    });
  };

  return {
    models: modelsQuery.data ?? [],
    loading: modelsQuery.isLoading,
    error: modelsQuery.error,
    retry: modelsQuery.refetch,
    form,
    editorOpen: open,
    editing,
    testResult,
    testFailed: testMutation.isError,
    saving: saveMutation.isPending,
    testing: testMutation.isPending,
    activating: activateMutation.isPending,
    openEditor,
    closeEditor,
    save: (values: ModelFormValues) => saveMutation.mutate(values),
    test: (values: ModelFormValues) => testMutation.mutate(values),
    activate: (id: string) => activateMutation.mutate(id),
    remove: (id: string) => deleteMutation.mutate(id),
  };
}
