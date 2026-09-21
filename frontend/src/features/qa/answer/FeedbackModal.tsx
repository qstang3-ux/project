import { Form, Input, Modal, Radio } from 'antd';
import { useState } from 'react';
import type { FeedbackReason } from '../../../api/types';

interface FeedbackModalProps {
  open: boolean;
  submitting: boolean;
  onCancel: () => void;
  onSubmit: (reason: FeedbackReason, description?: string) => void;
}

export function FeedbackModal({ open, submitting, onCancel, onSubmit }: FeedbackModalProps) {
  const [reason, setReason] = useState<FeedbackReason>('result_error');
  const [description, setDescription] = useState('');
  return (
    <Modal title="提交数据反馈" open={open} okText="提交反馈" cancelText="取消" confirmLoading={submitting} onCancel={onCancel} onOk={() => onSubmit(reason, description.trim() || undefined)} okButtonProps={{ disabled: reason === 'other' && !description.trim() }}>
      <Form layout="vertical">
        <Form.Item label="问题原因" required>
          <Radio.Group value={reason} onChange={(event) => setReason(event.target.value as FeedbackReason)}>
            <Radio value="sql_error">SQL 错误</Radio><Radio value="result_error">结果错误</Radio><Radio value="metric_error">口径错误</Radio><Radio value="answer_error">回答错误</Radio><Radio value="other">其他</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item label="补充说明" required={reason === 'other'}>
          <Input.TextArea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={500} showCount rows={4} placeholder="请描述需要校对的内容" />
        </Form.Item>
      </Form>
    </Modal>
  );
}
