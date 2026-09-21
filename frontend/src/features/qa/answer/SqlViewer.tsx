import { CheckCircleFilled, CloseCircleFilled, CodeOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { Collapse } from 'antd';
import type { ExecutionDetail } from '../../../api/types';
import { CopyButton } from '../../../components/CopyButton';

export function SqlViewer({ sql, validationStatus }: { sql: string; validationStatus: ExecutionDetail['sqlValidationStatus'] | undefined }) {
  const status = validationStatus ?? 'not_started';
  const validationState = {
    passed: { icon: <CheckCircleFilled />, label: '安全校验通过' },
    rejected: { icon: <CloseCircleFilled />, label: '安全校验拒绝' },
    not_started: { icon: <MinusCircleOutlined />, label: '尚未校验' },
  }[status];
  return (
    <Collapse className="sql-viewer" items={[{
      key: 'sql',
      label: (
        <span className="sql-viewer-heading">
          <span className="sql-viewer-icon"><CodeOutlined /></span>
          <span className="sql-viewer-title"><strong>生成 SQL</strong><small>由模型生成，经只读安全策略校验</small></span>
          <span className={`sql-validation sql-validation-${status}`}>{validationState.icon}{validationState.label}</span>
        </span>
      ),
      extra: <span className="sql-copy-action" onClick={(event) => event.stopPropagation()}><CopyButton text={sql} label="复制 SQL" /></span>,
      children: (
        <div className="sql-code-panel">
          <div className="sql-code-toolbar"><span><i />SQL 查询语句</span><span>只读</span></div>
          <pre tabIndex={0} aria-label="生成的 SQL"><code>{sql}</code></pre>
        </div>
      ),
    }]} />
  );
}
