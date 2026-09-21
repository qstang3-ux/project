import { useEffect, useState } from 'react';
import { AnswerMarkdown } from './AnswerMarkdown';

interface TypewriterTextProps {
  text: string;
  animate: boolean;
}

const FRAME_MS = 24;
const MAX_FRAMES = 75;

export function TypewriterText({ text, animate }: TypewriterTextProps) {
  const reduceMotion = typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const shouldAnimate = animate && !reduceMotion && text.length > 1;
  const [visibleLength, setVisibleLength] = useState(shouldAnimate ? 0 : text.length);

  useEffect(() => {
    if (!shouldAnimate) {
      setVisibleLength(text.length);
      return;
    }
    setVisibleLength(0);
    const chunkSize = Math.max(1, Math.ceil(text.length / MAX_FRAMES));
    const timer = window.setInterval(() => {
      setVisibleLength((current) => {
        const next = Math.min(text.length, current + chunkSize);
        if (next >= text.length) window.clearInterval(timer);
        return next;
      });
    }, FRAME_MS);
    return () => window.clearInterval(timer);
  }, [shouldAnimate, text]);

  const typing = shouldAnimate && visibleLength < text.length;
  if (!typing) return <AnswerMarkdown text={text} />;

  return (
    <p className="typewriter-text" aria-label={text}>
      <span aria-hidden="true">{text.slice(0, visibleLength)}</span>
      <span className="typewriter-cursor" aria-hidden="true" />
    </p>
  );
}
