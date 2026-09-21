import { CheckCircleOutlined, CloseCircleOutlined, CodeOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { Collapse, Tag } from 'antd';
import type { ExecutionDetail } from '../../../api/types';
import { CopyButton } from '../../../components/CopyButton';

export function SqlViewer({ sql, validationStatus }: { sql: string; validationStatus: ExecutionDetail['sqlValidationStatus'] | undefined }) {
  const validationTag = {
    passed: <Tag color="success" icon={<CheckCircleOutlined />}>安全校验通过</Tag>,
    rejected: <Tag color="error" icon={<CloseCircleOutlined />}>安全校验拒绝</Tag>,
    not_started: <Tag icon={<MinusCircleOutlined />}>尚未校验</Tag>,
  }[validationStatus ?? 'not_started'];
  return (
    <Collapse className="sql-viewer" items={[{
      key: 'sql',
      label: <span><CodeOutlined /> 生成 SQL {validationTag}</span>,
      extra: <span onClick={(event) => event.stopPropagation()}><CopyButton text={sql} label="复制 SQL" /></span>,
      children: <pre><code>{sql}</code></pre>,
    }]} />
  );
}
