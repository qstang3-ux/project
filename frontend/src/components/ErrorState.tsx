import { ReloadOutlined } from '@ant-design/icons';
import { Button, Result } from 'antd';
import { getErrorMessage } from '../api/errorMessages';

interface ErrorStateProps {
  title: string;
  error?: unknown;
  onRetry?: () => void;
  primaryAction?: boolean;
}

export function ErrorState({ title, error, onRetry, primaryAction = false }: ErrorStateProps) {
  return (
    <Result
      status="error"
      title={title}
      subTitle={getErrorMessage(error)}
      extra={onRetry ? <Button type={primaryAction ? 'primary' : 'default'} icon={<ReloadOutlined />} onClick={onRetry}>重试</Button> : undefined}
    />
  );
}
