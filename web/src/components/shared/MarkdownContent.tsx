import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

const components: Components = {
  // Downscale headings: h1/h2 -> smaller sizes since these are post bodies
  h1: ({ children }) => (
    <h4 className="text-base font-semibold text-text-primary mt-3 mb-1.5">
      {children}
    </h4>
  ),
  h2: ({ children }) => (
    <h5 className="text-[15px] font-semibold text-text-primary mt-3 mb-1.5">
      {children}
    </h5>
  ),
  h3: ({ children }) => (
    <h6 className="text-sm font-semibold text-text-primary mt-2.5 mb-1">
      {children}
    </h6>
  ),
  h4: ({ children }) => (
    <h6 className="text-sm font-medium text-text-secondary mt-2 mb-1">
      {children}
    </h6>
  ),
  p: ({ children }) => (
    <p className="text-[15px] leading-[1.7] text-text-primary mb-2 last:mb-0">
      {children}
    </p>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-outside ml-5 mb-2 space-y-0.5 text-[15px] leading-[1.7] text-text-primary">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside ml-5 mb-2 space-y-0.5 text-[15px] leading-[1.7] text-text-primary">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="pl-1">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-border-accent pl-3 my-2 text-text-secondary italic">
      {children}
    </blockquote>
  ),
  code: ({ children, className }) => {
    // Fenced code blocks get a className like "language-python"
    if (className) {
      return (
        <pre className="bg-bg-elevated rounded-md p-3 my-2 overflow-x-auto">
          <code className="text-sm text-text-primary font-mono">
            {children}
          </code>
        </pre>
      );
    }
    // Inline code
    return (
      <code className="bg-bg-elevated text-text-accent text-[13px] px-1.5 py-0.5 rounded font-mono">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-text-accent hover:underline"
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-text-primary">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  hr: () => <hr className="border-border-default my-3" />,
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="text-sm border-collapse w-full">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-border-default bg-bg-elevated px-3 py-1.5 text-left text-text-secondary font-medium text-xs">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-border-default px-3 py-1.5 text-text-primary text-sm">
      {children}
    </td>
  ),
};

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div className={className}>
      <ReactMarkdown components={components}>{content}</ReactMarkdown>
    </div>
  );
}
