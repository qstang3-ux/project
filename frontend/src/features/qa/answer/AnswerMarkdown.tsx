import type { ComponentPropsWithoutRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function AnswerMarkdown({ text }: { text: string }) {
  return (
    <div className="answer-markdown" aria-label={text}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          a: ({ children, ...props }: ComponentPropsWithoutRef<'a'>) => (
            <a {...props} target="_blank" rel="noreferrer noopener nofollow">{children}</a>
          ),
          img: ({ alt }: ComponentPropsWithoutRef<'img'>) => <span>{alt ?? '图片'}</span>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
