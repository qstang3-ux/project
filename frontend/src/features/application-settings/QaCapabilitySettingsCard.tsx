import { AudioOutlined, BulbOutlined, CustomerServiceOutlined, DatabaseOutlined, SettingOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { Button, Card, Form, InputNumber, Modal, Switch, Tooltip } from 'antd';
import { useState } from 'react';
import { ModelSettingsModal } from '../model-settings/ModelSettingsModal';
import { WelcomeSettingsCard } from './WelcomeSettingsCard';

const capabilities = [
  { name: 'followUpEnabled', icon: <BulbOutlined />, title: '推荐追问', description: '回答完成后给出下一步探索方向' },
  { name: 'ttsEnabled', icon: <CustomerServiceOutlined />, title: '语音播放', description: '使用设备音色朗读回答，零调用费' },
  { name: 'sttEnabled', icon: <AudioOutlined />, title: '语音输入', description: '将中文语音转成文字，不自动发送' },
  { name: 'modelQaEnabled', icon: <DatabaseOutlined />, title: '模型配置', description: '配置问数使用的真实模型与连接参数', settings: 'model' },
  { name: 'frequentQuestionsEnabled', icon: <ThunderboltOutlined />, title: '常问问题', description: '根据提问频次生成快捷问题', settings: 'frequent' },
] as const;

export function QaCapabilitySettingsCard() {
  const [modelSettingsOpen, setModelSettingsOpen] = useState(false);
  const [frequentSettingsOpen, setFrequentSettingsOpen] = useState(false);

  return (
    <>
      <Card className="settings-section-card" title={<div className="settings-card-title"><span><ThunderboltOutlined /></span><div><strong>应用能力</strong><small>按需启用和配置问数体验</small></div></div>}>
        <div className="capability-grid">
          <WelcomeSettingsCard />
          {capabilities.map((item) => (
            <div className="capability-tile" key={item.name}>
              <span className="capability-icon">{item.icon}</span>
              <span className="capability-copy"><strong>{item.title}</strong><small>{item.description}</small></span>
              <span className="capability-actions">
                {'settings' in item ? (
                  <Tooltip title={item.settings === 'model' ? '配置模型' : '常问设置'}>
                    <Button
                      type="text"
                      shape="circle"
                      icon={<SettingOutlined />}
                      aria-label={item.settings === 'model' ? '打开模型配置' : '编辑常问设置'}
                      onClick={() => item.settings === 'model' ? setModelSettingsOpen(true) : setFrequentSettingsOpen(true)}
                    />
                  </Tooltip>
                ) : null}
                <Form.Item name={item.name} valuePropName="checked" noStyle><Switch size="small" aria-label={`${item.title}开关`} /></Form.Item>
              </span>
            </div>
          ))}
        </div>
      </Card>
      <ModelSettingsModal open={modelSettingsOpen} onClose={() => setModelSettingsOpen(false)} />
      <Modal
        title="常问设置"
        open={frequentSettingsOpen}
        width={480}
        okText="完成"
        forceRender
        cancelButtonProps={{ style: { display: 'none' } }}
        onOk={() => setFrequentSettingsOpen(false)}
        onCancel={() => setFrequentSettingsOpen(false)}
      >
        <p className="settings-modal-intro">达到设定频次后，问题会进入快捷提问的常问列表。修改后自动保存。</p>
        <Form.Item name="frequentQuestionThreshold" label="进入常问列表的提问次数" rules={[{ required: true }]}>
          <InputNumber className="settings-modal-number" min={1} max={1000} />
        </Form.Item>
      </Modal>
    </>
  );
}
