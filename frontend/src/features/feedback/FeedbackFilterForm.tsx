import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, Form, Input, Select, Space, type FormInstance } from 'antd';
import { reasonLabels, statusLabels } from './feedbackPresentation';
import type { FeedbackFilters } from './feedbackTypes';

interface FeedbackFilterFormProps {
  form: FormInstance<FeedbackFilters>;
  onSubmit: (values: FeedbackFilters) => void;
  onReset: () => void;
}

export function FeedbackFilterForm({ form, onSubmit, onReset }: FeedbackFilterFormProps) {
  return (
    <Form<FeedbackFilters> className="feedback-filter" form={form} layout="vertical" onFinish={onSubmit}>
      <Form.Item name="keyword" label="关键词"><Input allowClear prefix={<SearchOutlined />} placeholder="问题关键词" /></Form.Item>
      <Form.Item name="userId" label="用户"><Input allowClear placeholder="用户标识" /></Form.Item>
      <Form.Item name="reason" label="原因"><Select allowClear placeholder="全部原因" options={Object.entries(reasonLabels).map(([value, label]) => ({ value, label }))} /></Form.Item>
      <Form.Item name="status" label="状态"><Select allowClear placeholder="全部状态" options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))} /></Form.Item>
      <Form.Item className="feedback-filter-actions"><Space><Button type="primary" htmlType="submit" icon={<SearchOutlined />}>查询</Button><Button icon={<ReloadOutlined />} onClick={onReset}>重置</Button></Space></Form.Item>
    </Form>
  );
}
