import { useEffect, useRef, useState, type PointerEventHandler, type UIEventHandler, type WheelEventHandler } from 'react';
import type { ExecutionStatus } from '../../../api/types';

interface ConversationScrollOptions {
  sessionId?: string;
  messageCount: number;
  executionId?: string;
  executionStatus?: ExecutionStatus;
}

export function useConversationScroll(options: ConversationScrollOptions) {
  const conversationRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const pointerScrollingRef = useRef(false);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const container = conversationRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior });
    stickToBottomRef.current = true;
    pointerScrollingRef.current = false;
    setShowScrollToBottom(false);
  };

  useEffect(() => {
    stickToBottomRef.current = true;
  }, [options.sessionId]);

  useEffect(() => {
    if (!stickToBottomRef.current) return;
    const frame = window.requestAnimationFrame(() => scrollToBottom('auto'));
    return () => window.cancelAnimationFrame(frame);
  }, [options.sessionId, options.messageCount, options.executionId, options.executionStatus]);

  useEffect(() => {
    const container = conversationRef.current;
    if (!container || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      if (stickToBottomRef.current) container.scrollTop = container.scrollHeight;
    });
    observer.observe(container);
    Array.from(container.children).forEach((child) => observer.observe(child));
    return () => observer.disconnect();
  }, [options.sessionId, options.messageCount, options.executionId]);

  const onWheel: WheelEventHandler<HTMLDivElement> = (event) => {
    if (event.deltaY >= 0) return;
    stickToBottomRef.current = false;
    setShowScrollToBottom(true);
  };

  const onPointerDown: PointerEventHandler<HTMLDivElement> = () => {
    pointerScrollingRef.current = true;
  };

  const stopPointerScrolling: PointerEventHandler<HTMLDivElement> = () => {
    pointerScrollingRef.current = false;
  };

  const onScroll: UIEventHandler<HTMLDivElement> = (event) => {
    const container = event.currentTarget;
    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distanceToBottom < 120) {
      stickToBottomRef.current = true;
      setShowScrollToBottom(false);
    } else if (pointerScrollingRef.current) {
      stickToBottomRef.current = false;
      setShowScrollToBottom(true);
    }
  };

  return {
    conversationRef,
    showScrollToBottom,
    scrollToBottom,
    scrollHandlers: { onWheel, onPointerDown, onPointerUp: stopPointerScrolling, onPointerLeave: stopPointerScrolling, onScroll },
    markForAutoScroll: () => { stickToBottomRef.current = true; },
  };
}
