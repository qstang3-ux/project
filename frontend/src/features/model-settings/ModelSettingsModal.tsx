import { PlusOutlined } from '@ant-design/icons';
import { Button, Modal } from 'antd';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { ModelConfigDialog } from './ModelConfigDialog';
import { ModelConfigCards } from './ModelConfigCards';
import { useModelSettings } from './useModelSettings';

interface ModelSettingsModalProps {
  open: boolean;
  onClose: () => void;
}

export function ModelSettingsModal({ open, onClose }: ModelSettingsModalProps) {
  const settings = useModelSettings();

  return (
    <>
      <Modal
        className="model-settings-modal"
        title={<div><strong>模型配置</strong><small>管理问数使用的真实模型连接</small></div>}
        open={open}
        width="min(1080px, calc(100vw - 48px))"
        footer={null}
        onCancel={onClose}
        destroyOnHidden={false}
      >
        <div className="model-settings-modal-toolbar">
          <p>为智能问数选择当前模型；连接凭据保存后将不再显示。</p>
        </div>
        {settings.error ? <ErrorState title="模型配置加载失败" error={settings.error} onRetry={() => void settings.retry()} /> : null}
        {!settings.error && !settings.loading && settings.models.length === 0 ? (
          <EmptyState title="还没有模型配置" description="添加一个 OpenAI-compatible 模型后即可启用真实问数。" action={<Button type="primary" icon={<PlusOutlined />} onClick={() => settings.openEditor()}>新增模型</Button>} />
        ) : (
          <ModelConfigCards models={settings.models} loading={settings.loading} activating={settings.activating} onAdd={() => settings.openEditor()} onEdit={settings.openEditor} onActivate={settings.activate} onDelete={settings.remove} />
        )}
      </Modal>
      <ModelConfigDialog open={settings.editorOpen} editing={settings.editing} form={settings.form} saving={settings.saving} testing={settings.testing} testResult={settings.testResult} testFailed={settings.testFailed} onCancel={settings.closeEditor} onSave={settings.save} onTest={settings.test} />
    </>
  );
}
