import { Form, Input, Modal, Select, type FormInstance } from 'antd';
import type { FeedbackUpdate } from '../../api/types';
import { statusLabels } from './feedbackPresentation';

interface FeedbackProcessDialogProps {
  open: boolean;
  form: FormInstance<FeedbackUpdate>;
  saving: boolean;
  onCancel: () => void;
  onSave: (values: FeedbackUpdate) => void;
}

export function FeedbackProcessDialog({ open, form, saving, onCancel, onSave }: FeedbackProcessDialogProps) {
  return (
    <Modal title="处理反馈" open={open} okText="保存" cancelText="取消" confirmLoading={saving} onCancel={onCancel} onOk={() => form.submit()}>
      <Form<FeedbackUpdate> form={form} layout="vertical" onFinish={onSave}>
        <Form.Item name="status" label="处理状态" rules={[{ required: true }]}><Select options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))} /></Form.Item>
        <Form.Item name="resolutionNote" label="处理备注" rules={[{ max: 2000 }]}><Input.TextArea rows={6} maxLength={2000} showCount /></Form.Item>
        <Form.Item name="version" hidden><Input /></Form.Item>
      </Form>
    </Modal>
  );
}
