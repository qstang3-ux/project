import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, DatePicker, Form, Input, Select, Space, type FormInstance } from 'antd';
import type { Dayjs } from 'dayjs';
import type { ExecutionStatus } from '../../api/types';
import { executionStatusLabels } from './qaLogPresentation';

export interface QaLogFilterValues { keyword?: string; userId?: string; status?: ExecutionStatus; range?: [Dayjs, Dayjs] }

export function QaLogFilter({ form, onSubmit, onReset }: { form: FormInstance<QaLogFilterValues>; onSubmit: (values: QaLogFilterValues) => void; onReset: () => void }) {
  return <Form<QaLogFilterValues> className="qa-log-filter" form={form} layout="vertical" onFinish={onSubmit}>
    <Form.Item name="keyword" label="问题关键词"><Input allowClear prefix={<SearchOutlined />} placeholder="搜索用户问题" /></Form.Item>
    <Form.Item name="userId" label="用户"><Input allowClear placeholder="用户标识" /></Form.Item>
    <Form.Item name="status" label="执行状态"><Select allowClear placeholder="全部状态" options={Object.entries(executionStatusLabels).map(([value, label]) => ({ value, label }))} /></Form.Item>
    <Form.Item name="range" label="时间范围"><DatePicker.RangePicker showTime allowClear /></Form.Item>
    <Form.Item className="qa-log-filter-actions"><Space><Button type="primary" htmlType="submit" icon={<SearchOutlined />}>查询</Button><Button icon={<ReloadOutlined />} onClick={onReset}>重置</Button></Space></Form.Item>
  </Form>;
}
