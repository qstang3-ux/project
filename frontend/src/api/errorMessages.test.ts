import { describe, expect, it } from 'vitest';
import { ApiError } from './client';
import { getErrorMessage } from './errorMessages';

describe('getErrorMessage', () => {
  it('maps server error codes without exposing details', () => {
    const error = new ApiError(504, { code: 'QUERY_TIMEOUT', message: 'database connection string', requestId: 'req-1', details: { stack: 'secret' } });
    expect(getErrorMessage(error)).toBe('查询执行超时，请缩小问题范围后重试。');
    expect(getErrorMessage(error)).not.toContain('connection');
  });
});
