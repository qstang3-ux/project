import { CheckOutlined, CopyOutlined } from '@ant-design/icons';
import { App, Button, Tooltip } from 'antd';
import { useState } from 'react';

interface CopyButtonProps {
  text: string;
  label?: string;
}

export function CopyButton({ text, label = '复制' }: CopyButtonProps) {
  const { message } = App.useApp();
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      void message.success('已复制');
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      void message.error('剪贴板不可用，请手动复制。');
    }
  };
  return <Tooltip title={copied ? '已复制' : label}><Button className="icon-button icon-button-quiet" type="text" size="small" icon={copied ? <CheckOutlined /> : <CopyOutlined />} onClick={() => void copy()} aria-label={copied ? '已复制' : label} /></Tooltip>;
}
