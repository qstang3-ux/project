import { ApiError } from './client';

const codeMessages: Record<string, string> = {
  VALIDATION_ERROR: '提交内容有误，请检查后重试。',
  RESOURCE_NOT_FOUND: '请求的资源不存在或已被删除。',
  VERSION_CONFLICT: '数据已被其他操作更新，请刷新后重试。',
  MODEL_NOT_CONFIGURED: '尚未配置可用模型，请先完成模型配置。',
  MODEL_AUTH_FAILED: '模型鉴权失败，请检查服务端密钥配置。',
  MODEL_TIMEOUT: '模型响应超时，请稍后重试。',
  DATA_SOURCE_UNAVAILABLE: '所选数据源当前不可用。',
  SQL_VALIDATION_FAILED: '该请求无法生成符合只读安全规则的查询。',
  QUERY_TIMEOUT: '查询执行超时，请缩小问题范围后重试。',
  EXECUTION_CANCELLED: '本次问数已停止。',
  RATE_LIMITED: '请求过于频繁，请稍后再试。',
  NETWORK_ERROR: '网络连接失败，请检查网络后重试。',
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return codeMessages[error.code] ?? error.message;
  return '发生未知错误，请稍后重试。';
}
