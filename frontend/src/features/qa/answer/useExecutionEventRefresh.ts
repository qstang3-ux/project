import { useEffect, useRef } from 'react';
import { api } from '../../../api/client';
import { createFetchEventSource } from '../../../api/fetchEventSource';
import type { ExecutionStatus } from '../../../api/types';
import { ExecutionEventStream } from './executionEventStream';

export function useExecutionEventRefresh(executionId: string, status: ExecutionStatus | undefined, refresh: () => void) {
  const refreshRef = useRef(refresh);
  const statusRef = useRef(status);
  const streamRef = useRef<ExecutionEventStream | undefined>(undefined);
  refreshRef.current = refresh;
  statusRef.current = status;

  useEffect(() => {
    const stream = new ExecutionEventStream({
      executionId,
      initialStatus: statusRef.current,
      refresh: () => refreshRef.current(),
      createEventSource: createFetchEventSource,
      eventsUrl: api.executionEventsUrl,
      checkCursor: api.checkExecutionEventCursor,
    });
    streamRef.current = stream;
    return () => {
      stream.dispose();
      if (streamRef.current === stream) streamRef.current = undefined;
    };
  }, [executionId]);

  useEffect(() => {
    streamRef.current?.updateStatus(status);
  }, [status]);
}
