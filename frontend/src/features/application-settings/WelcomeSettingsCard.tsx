import { MessageOutlined, SettingOutlined } from '@ant-design/icons';
import { Button, Form, Input, Modal, Switch, Tooltip } from 'antd';
import { useState } from 'react';
import { RecommendedQuestionsField } from './RecommendedQuestionsField';

export function WelcomeSettingsCard() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="capability-tile">
        <span className="capability-icon capability-icon-blue"><MessageOutlined /></span>
        <span className="capability-copy"><strong>对话开场白</strong><small>配置新对话的欢迎语和推荐问题</small></span>
        <span className="capability-actions">
          <Tooltip title="编辑开场白">
            <Button type="text" shape="circle" icon={<SettingOutlined />} aria-label="编辑对话开场白" onClick={() => setOpen(true)} />
          </Tooltip>
          <Form.Item name="greetingEnabled" valuePropName="checked" noStyle><Switch size="small" aria-label="对话开场白开关" /></Form.Item>
        </span>
      </div>
      <Modal
        className="greeting-settings-modal"
        title="对话开场白"
        open={open}
        width={680}
        okText="完成编辑"
        forceRender
        cancelButtonProps={{ style: { display: 'none' } }}
        onOk={() => setOpen(false)}
        onCancel={() => setOpen(false)}
      >
        <p className="settings-modal-intro">设置新对话展示的欢迎内容和推荐问题，修改后自动保存。</p>
        <Form.Item className="greeting-editor" name="greetingText" label="开场白内容" rules={[{ required: true, message: '请输入开场白' }, { max: 1000 }]}> 
          <Input.TextArea rows={4} showCount maxLength={1000} />
        </Form.Item>
        <RecommendedQuestionsField />
      </Modal>
    </>
  );
}
