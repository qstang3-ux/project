import { ApiOutlined, KeyOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { Alert, Button, Form, Input, InputNumber, Modal, Select, Space, Switch, type FormInstance } from 'antd';
import { useEffect, useState } from 'react';
import type { ModelConfig } from '../../api/types';
import type { ModelFormValues } from './modelForm';

interface ModelConfigDialogProps {
  open: boolean;
  editing?: ModelConfig;
  form: FormInstance<ModelFormValues>;
  saving: boolean;
  testing: boolean;
  testResult?: string;
  testFailed: boolean;
  onCancel: () => void;
  onSave: (values: ModelFormValues) => void;
  onTest: (values: ModelFormValues) => void;
}

export function ModelConfigDialog(props: ModelConfigDialogProps) {
  const busy = props.saving || props.testing;
  const [replacingApiKey, setReplacingApiKey] = useState(false);

  useEffect(() => {
    if (props.open) setReplacingApiKey(false);
  }, [props.editing?.id, props.open]);

  const cancelApiKeyReplacement = () => {
    props.form.setFieldValue('apiKey', '');
    setReplacingApiKey(false);
  };

  return (
    <Modal title={props.editing ? '编辑模型' : '新增模型'} open={props.open} zIndex={1200} onCancel={props.onCancel} onOk={() => props.form.submit()} okText="保存" cancelText="取消" confirmLoading={props.saving} cancelButtonProps={{ disabled: busy }} maskClosable={false} keyboard={!busy} forceRender>
      <Form<ModelFormValues> form={props.form} layout="vertical" onFinish={props.onSave}>
        <Form.Item name="name" label="配置名称" rules={[{ required: true }, { max: 100 }]}><Input /></Form.Item>
        <Form.Item name="provider" label="供应商" rules={[{ required: true }]}><Input disabled prefix={<ApiOutlined />} /></Form.Item>
        <Form.Item name="protocol" label="接口协议" rules={[{ required: true }]}><Select options={[{ value: 'responses', label: 'Responses API' }, { value: 'chat_completions', label: 'Chat Completions' }]} /></Form.Item>
        <Form.Item name="baseUrl" label="Base URL" rules={[{ required: true }, { type: 'url' }]}><Input placeholder="https://api.example.com/v1" /></Form.Item>
        <Form.Item name="modelName" label="模型名称" rules={[{ required: true }, { max: 200 }]}><Input /></Form.Item>
        {props.editing && !replacingApiKey ? (
          <div className="model-secret-locked">
            <span><KeyOutlined /></span>
            <div><strong>API Key 已安全保存</strong><small>出于安全考虑，已保存的密钥不可查看。</small></div>
            <Button onClick={() => setReplacingApiKey(true)}>更换 API Key</Button>
          </div>
        ) : (
          <Form.Item
            name="apiKey"
            label={props.editing ? '新的 API Key' : 'API Key'}
            extra={props.editing ? <Button type="link" className="model-secret-cancel" onClick={cancelApiKeyReplacement}>取消更换</Button> : '仅在首次新增时输入，保存后不再回显。'}
            rules={[{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password autoComplete="new-password" placeholder="请输入服务商提供的密钥" visibilityToggle={false} />
          </Form.Item>
        )}
        <Form.Item name="timeoutSeconds" label="超时时间（秒）" rules={[{ required: true }]}><InputNumber min={1} max={120} /></Form.Item>
        <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
        <Space>
          <Button icon={<ThunderboltOutlined />} loading={props.testing} onClick={() => void props.form.validateFields().then(props.onTest)}>{props.editing && !replacingApiKey ? '测试已保存连接' : '测试连接'}</Button>
          {props.testResult ? <Alert type={props.testFailed ? 'error' : 'success'} showIcon message={props.testResult} /> : null}
        </Space>
      </Form>
    </Modal>
  );
}
