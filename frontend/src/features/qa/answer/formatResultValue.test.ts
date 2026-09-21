import { describe, expect, it } from 'vitest';
import { formatResultValue } from './formatResultValue';

describe('formatResultValue', () => {
  it('formats numeric values and nulls consistently', () => {
    expect(formatResultValue('7950.5', 'decimal')).toBe('7,950.5');
    expect(formatResultValue(72, 'percent')).toBe('72%');
    expect(formatResultValue(2026, 'integer', 'analysis_year')).toBe('2026');
    expect(formatResultValue(null, 'string')).toBe('--');
  });

  it('keeps untrusted text as plain text', () => {
    expect(formatResultValue('<script>alert(1)</script>', 'string')).toBe('<script>alert(1)</script>');
  });
});
