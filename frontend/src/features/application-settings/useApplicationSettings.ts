import { App, Form } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../api/client';
import { getErrorMessage } from '../../api/errorMessages';
import { queryKeys } from '../../api/queryKeys';
import type { ApplicationConfigUpdate } from '../../api/types';
import { buildApplicationConfigUpdate } from './applicationConfigPayload';

export function useApplicationSettings() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<ApplicationConfigUpdate>();
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const revision = useRef(0);
  const savingRef = useRef(false);
  const queuedRef = useRef(false);
  const hydratedVersion = useRef<number | undefined>(undefined);
  const versionRef = useRef<number | undefined>(undefined);
  const configQuery = useQuery({ queryKey: queryKeys.applicationConfig, queryFn: api.getApplicationConfig });

  const flushSave = useCallback(async () => {
    if (savingRef.current) {
      queuedRef.current = true;
      return;
    }

    const startedRevision = revision.current;
    try {
      if (!configQuery.data) return;
      if (form.getFieldsError().some((field) => field.errors.length > 0)) return;
      const draft = form.getFieldsValue(true) as Partial<ApplicationConfigUpdate>;
      const values = {
        ...buildApplicationConfigUpdate(configQuery.data, draft),
        version: versionRef.current ?? configQuery.data.version,
      };
      savingRef.current = true;
      setSaving(true);
      const config = await api.updateApplicationConfig(values);
      hydratedVersion.current = config.version;
      versionRef.current = config.version;
      queryClient.setQueryData(queryKeys.applicationConfig, config);
      if (startedRevision === revision.current) setDirty(false);
    } catch (error) {
      void message.error(getErrorMessage(error));
    } finally {
      savingRef.current = false;
      setSaving(false);
      if (queuedRef.current || startedRevision !== revision.current) {
        queuedRef.current = false;
        saveTimer.current = setTimeout(() => void flushSave(), 300);
      }
    }
  }, [configQuery.data, form, message, queryClient]);

  useEffect(() => {
    if (configQuery.data && !dirty && hydratedVersion.current !== configQuery.data.version) {
      form.setFieldsValue({
        ...configQuery.data,
        recommendedQuestions: [...configQuery.data.recommendedQuestions],
      });
      hydratedVersion.current = configQuery.data.version;
      versionRef.current = configQuery.data.version;
    }
  }, [configQuery.data, dirty, form]);

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault(); };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [dirty]);

  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current); }, []);

  const markDirty = () => {
    setDirty(true);
    revision.current += 1;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => void flushSave(), 650);
  };

  return {
    form,
    dirty,
    config: configQuery.data,
    loading: configQuery.isLoading,
    error: configQuery.error,
    saving,
    retry: configQuery.refetch,
    markDirty,
  };
}
