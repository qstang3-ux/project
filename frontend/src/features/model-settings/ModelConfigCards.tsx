import {
  CheckCircleFilled,
  CloudServerOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  RobotOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Button, Popconfirm, Select, Skeleton, Tag } from 'antd';
import type { ModelConfig } from '../../api/types';

interface ModelConfigCardsProps {
  models: ModelConfig[];
  loading: boolean;
  activating: boolean;
  onAdd: () => void;
  onEdit: (model: ModelConfig) => void;
  onActivate: (id: string) => void;
  onDelete: (id: string) => void;
}

const ADD_MODEL_VALUE = '__add_model__';

const protocolLabels: Record<ModelConfig['protocol'], string> = {
  responses: 'Responses API',
  chat_completions: 'Chat Completions',
};

export function ModelConfigCards({ models, loading, activating, onAdd, onEdit, onActivate, onDelete }: ModelConfigCardsProps) {
  if (loading) return <Skeleton active paragraph={{ rows: 5 }} />;

  const activeModel = models.find((model) => model.isActive);
  const selectOptions = [
    ...models.map((model) => ({
      value: model.id,
      label: `${model.name} · ${model.modelName}`,
      disabled: !model.enabled,
    })),
    { value: ADD_MODEL_VALUE, label: '＋ 新增模型' },
  ];

  return (
    <div className="model-scene-config">
      <section className="model-scene-card" aria-label="智能问数模型配置">
        <div className="model-scene-heading">
          <span className="model-scene-icon"><RobotOutlined /></span>
          <div>
            <strong>智能问数模型</strong>
            <small>选择 AI 问数、SQL 生成与分析总结使用的模型</small>
          </div>
        </div>
        <div className="model-scene-control">
          <Select
            aria-label="当前问数模型"
            className="model-scene-select"
            value={activeModel?.id}
            placeholder="请选择模型"
            options={selectOptions}
            loading={activating}
            onChange={(value) => value === ADD_MODEL_VALUE ? onAdd() : onActivate(value)}
          />
          <Button
            aria-label="编辑当前模型"
            icon={<SettingOutlined />}
            disabled={!activeModel}
            onClick={() => activeModel && onEdit(activeModel)}
          >
            配置
          </Button>
        </div>
      </section>

      <div className="model-connection-heading">
        <div>
          <strong>已接入模型</strong>
          <small>连接凭据已由服务端加密保存，不在页面中回显</small>
        </div>
        <Button type="text" icon={<PlusOutlined />} onClick={onAdd}>新增模型</Button>
      </div>

      <div className="model-connection-list" aria-label="已接入模型列表">
        {models.map((model) => (
          <section className={`model-connection-row${model.isActive ? ' is-active' : ''}`} key={model.id} aria-label={`模型 ${model.name}`}>
            <span className="model-connection-icon"><CloudServerOutlined /></span>
            <div className="model-connection-name">
              <strong title={model.name}>{model.name}</strong>
              <small title={model.modelName}>{model.modelName}</small>
            </div>
            <div className="model-connection-meta">
              <span>{protocolLabels[model.protocol]}</span>
              <span title={model.baseUrl}>{model.baseUrl}</span>
            </div>
            <div className="model-connection-state">
              {model.isActive ? <Tag color="success" icon={<CheckCircleFilled />}>当前模型</Tag> : <Tag>{model.enabled ? '已接入' : '已停用'}</Tag>}
            </div>
            <div className="model-connection-actions">
              <Button type="text" icon={<EditOutlined />} aria-label={`编辑模型 ${model.name}`} onClick={() => onEdit(model)} />
              <Popconfirm title="删除模型配置？" description={model.isActive ? '当前模型不能删除，请先切换模型。' : '删除后无法恢复。'} disabled={model.isActive} onConfirm={() => onDelete(model.id)}>
                <Button type="text" danger icon={<DeleteOutlined />} aria-label={`删除模型 ${model.name}`} disabled={model.isActive} />
              </Popconfirm>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
