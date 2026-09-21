import { describe, expect, it } from 'vitest';
import { parseEventBlock } from './fetchEventSource';

describe('parseEventBlock', () => {
  it('parses named events, multi-line data, and stable IDs', () => {
    expect(parseEventBlock('id: execution-a:2\nevent: schema.selected\ndata: {"first":true}\ndata: tail')).toEqual({
      type: 'schema.selected',
      data: '{"first":true}\ntail',
      id: 'execution-a:2',
    });
  });

  it('ignores comments and blocks without data', () => {
    expect(parseEventBlock(': heartbeat\nid: execution-a:3')).toBeUndefined();
  });
});
