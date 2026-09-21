import type { ExecutionStatus } from '../../api/types';

export const executionStatusLabels: Record<ExecutionStatus, string> = {
  queued: '排队中', running: '执行中', awaiting_input: '待补充', completed: '已完成', failed: '失败', cancelled: '已停止', rejected: '安全拒绝',
};

export const executionStatusColors: Record<ExecutionStatus, string> = {
  queued: 'default', running: 'processing', awaiting_input: 'warning', completed: 'success', failed: 'error', cancelled: 'default', rejected: 'error',
};

export const modelPurposeLabels: Record<string, string> = {
  intent_classification: '意图识别', sql_generation: 'SQL 生成', sql_correction: 'SQL 纠错', answer_generation: '回答生成',
};
