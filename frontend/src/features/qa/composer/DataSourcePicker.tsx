import { CheckOutlined, ClearOutlined, DatabaseOutlined, DownOutlined, SelectOutlined } from '@ant-design/icons';
import { Alert, Button, Checkbox, Drawer, Empty, Skeleton } from 'antd';
import { useState } from 'react';
import type { DataSource } from '../../../api/types';

interface DataSourcePickerProps {
  sources: DataSource[];
  selectedIds: string[];
  loading: boolean;
  error: boolean;
  maxSelection: number;
  onChange: (ids: string[]) => void;
}

export function DataSourcePicker({ sources, selectedIds, loading, error, maxSelection, onChange }: DataSourcePickerProps) {
  const [open, setOpen] = useState(false);
  const enabled = sources.filter((source) => source.enabled);
  const selectedNames = sources.filter((source) => selectedIds.includes(source.id)).map((source) => source.name);
  const triggerLabel = selectedNames.length === 1
    ? selectedNames[0]
    : selectedIds.length > 0
      ? `${String(selectedIds.length)} 个数据源`
      : '选择数据源';

  const toggle = (id: string, checked: boolean) => {
    if (checked && selectedIds.length >= maxSelection) return;
    onChange(checked ? [...selectedIds, id] : selectedIds.filter((value) => value !== id));
  };

  return (
    <>
      <Button
        icon={<DatabaseOutlined />}
        aria-label={`选择数据源，当前已选 ${String(selectedIds.length)} 个`}
        onClick={() => setOpen(true)}
        className="source-trigger"
      >
        <span className="source-trigger-label">{triggerLabel}</span>
        <DownOutlined className="source-trigger-chevron" />
      </Button>
      <Drawer title="选择数据源" width={430} open={open} onClose={() => setOpen(false)} extra={<Button type="primary" icon={<CheckOutlined />} onClick={() => setOpen(false)}>完成</Button>}>
        <p className="muted">已选 {selectedIds.length}/{maxSelection} 个数据源。问数请求会明确携带这些数据源 ID。</p>
        <div className="source-actions"><Button size="small" icon={<SelectOutlined />} onClick={() => onChange(enabled.slice(0, maxSelection).map((item) => item.id))}>全选可用</Button><Button size="small" icon={<ClearOutlined />} onClick={() => onChange([])}>取消全选</Button></div>
        {loading ? <Skeleton active /> : null}
        {error ? <Alert type="error" showIcon message="数据源加载失败" description="暂时无法发送问题，请稍后重试。" /> : null}
        {!loading && !error && sources.length === 0 ? <Empty description="暂无数据源" /> : null}
        {(['ledger', 'report'] as const).map((group) => {
          const grouped = sources.filter((source) => source.group === group);
          if (!grouped.length) return null;
          return <section key={group} className="source-group"><h3>{group === 'ledger' ? '台账数据' : '统计报表'}</h3>{grouped.map((source) => (
            <label key={source.id} className={`source-option ${source.enabled ? '' : 'disabled'}`}>
              <Checkbox checked={selectedIds.includes(source.id)} disabled={!source.enabled || (!selectedIds.includes(source.id) && selectedIds.length >= maxSelection)} onChange={(event) => toggle(source.id, event.target.checked)} />
              <span><strong>{source.name}</strong><small>{source.description}</small><small>数据截至 {source.dataAsOf}{source.unavailableReason ? ` · ${source.unavailableReason}` : ''}</small></span>
            </label>
          ))}</section>;
        })}
        {selectedNames.length ? <Alert type="info" showIcon message={`当前选择：${selectedNames.join('、')}`} /> : null}
      </Drawer>
    </>
  );
}
