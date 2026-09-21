import { Skeleton, Tag } from 'antd';
import { ErrorState } from '../../components/ErrorState';
import { ApplicationConfigForm } from './ApplicationConfigForm';
import { useApplicationSettings } from './useApplicationSettings';

export function ApplicationSettings() {
  const settings = useApplicationSettings();

  if (settings.loading) return <div className="page-shell"><Skeleton active paragraph={{ rows: 12 }} /></div>;
  if (settings.error || !settings.config) {
    return <ErrorState title="应用配置加载失败" error={settings.error} onRetry={() => void settings.retry()} />;
  }

  return (
    <div className="page-shell settings-page">
      <div className="settings-page-header">
        <div className="settings-breadcrumb"><span>系统设置</span><i>/</i><strong>应用配置</strong></div>
        <div className="settings-title-row">
          <div className="page-heading"><h1>应用配置</h1><p>管理对话体验、智能能力和模型连接。</p></div>
          <Tag className="settings-status" color={settings.saving || settings.dirty ? 'processing' : 'success'}>
            {settings.saving || settings.dirty ? '正在自动保存…' : '已自动保存'}
          </Tag>
        </div>
      </div>
      <ApplicationConfigForm form={settings.form} onChange={settings.markDirty} />
    </div>
  );
}
