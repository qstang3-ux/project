import { describe, expect, it } from 'vitest';
import { createClarificationIdempotencyKey } from './idempotency';

describe('createClarificationIdempotencyKey', () => {
  it('is stable across retries and changes with round or content', () => {
    const first = createClarificationIdempotencyKey('execution-1', 1, ' 2026 年 ');
    expect(createClarificationIdempotencyKey('execution-1', 1, '2026 年')).toBe(first);
    expect(createClarificationIdempotencyKey('execution-1', 2, '2026 年')).not.toBe(first);
    expect(createClarificationIdempotencyKey('execution-1', 1, '2025 年')).not.toBe(first);
    expect(first.length).toBeGreaterThanOrEqual(8);
    expect(first.length).toBeLessThanOrEqual(128);
  });
});
