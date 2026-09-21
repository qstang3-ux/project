import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Form, Input, Space } from 'antd';

export function RecommendedQuestionsField() {
  return (
    <Form.List name="recommendedQuestions">
      {(fields, { add, remove }) => (
        <div className="question-list">
          <div className="field-heading"><div><strong>推荐问题</strong><span>显示在欢迎页，点击后只回填输入框</span></div><small>{fields.length}/10</small></div>
          {fields.map(({ key, ...field }, index) => (
            <Space key={key} align="start" className="question-row">
              <span className="question-index">{String(index + 1).padStart(2, '0')}</span>
              <Form.Item {...field} rules={[{ required: true, whitespace: true, message: '推荐问题不能为空' }, { max: 200 }]}> 
                <Input maxLength={200} showCount />
              </Form.Item>
              <Button className="field-icon-button" danger type="text" icon={<DeleteOutlined />} onClick={() => remove(field.name)} aria-label={`删除问题 ${String(index + 1)}`} />
            </Space>
          ))}
          <Button className="secondary-command" icon={<PlusOutlined />} disabled={fields.length >= 10} onClick={() => add('')}>添加推荐问题</Button>
        </div>
      )}
    </Form.List>
  );
}
