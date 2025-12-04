/**
 * CodeBlock component - displays code with syntax highlighting and copy button
 */

import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export interface CodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
}

export function CodeBlock({ code, language = 'sql', showLineNumbers = false }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-container relative group my-3">
      {/* Header with language and copy button */}
      <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border border-border rounded-t-md">
        <span className="text-xs font-mono text-muted-foreground uppercase">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-muted transition-colors"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check size={12} />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy size={12} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code content */}
      <div className="relative">
        <pre className="overflow-x-auto p-4 bg-muted border border-t-0 border-border rounded-b-md">
          <code className={`text-sm font-mono ${showLineNumbers ? 'line-numbers' : ''}`}>
            {code}
          </code>
        </pre>
      </div>
    </div>
  );
}

/**
 * InlineCode component - for inline code snippets
 */
export interface InlineCodeProps {
  children: string;
}

export function InlineCode({ children }: InlineCodeProps) {
  return (
    <code className="px-1.5 py-0.5 bg-muted text-sm font-mono rounded">
      {children}
    </code>
  );
}
