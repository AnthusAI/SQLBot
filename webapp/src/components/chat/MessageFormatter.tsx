/**
 * MessageFormatter component - parses message content and renders appropriate components
 * Handles code blocks, data tables, markdown, etc.
 */

import ReactMarkdown from 'react-markdown';
import { CodeBlock, InlineCode } from './CodeBlock';
import { DataTable, EmptyDataTable } from './DataTable';
import { CollapsibleSection, DetailSection } from './CollapsibleSection';
import { Database, Code } from 'lucide-react';

export interface MessageFormatterProps {
  content: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
}

/**
 * Parse markdown table into columns and rows
 */
function parseMarkdownTable(tableText: string): { columns: string[]; rows: string[][] } | null {
  const lines = tableText.trim().split('\n');
  if (lines.length < 3) return null;

  // Parse header
  const headerLine = lines[0].trim();
  if (!headerLine.startsWith('|') || !headerLine.endsWith('|')) return null;

  const columns = headerLine
    .split('|')
    .slice(1, -1)
    .map((col) => col.trim())
    .filter((col) => col.length > 0);

  // Skip separator line (lines[1])

  // Parse data rows
  const rows: string[][] = [];
  for (let i = 2; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line.startsWith('|') || !line.endsWith('|')) continue;

    const cells = line
      .split('|')
      .slice(1, -1)
      .map((cell) => cell.trim());

    if (cells.length === columns.length) {
      rows.push(cells);
    }
  }

  return { columns, rows };
}

/**
 * Parse and format message content
 */
export function MessageFormatter({ content, role }: MessageFormatterProps) {
  // For system messages, check if it contains query results with a markdown table
  if (role === 'system' && content.includes('📊 Query results:')) {
    // Extract the table part
    const lines = content.split('\n');
    const tableStartIndex = lines.findIndex((line) => line.trim().startsWith('|'));

    if (tableStartIndex !== -1) {
      // Split into header text and table
      const headerText = lines.slice(0, tableStartIndex).join('\n');
      const tableText = lines.slice(tableStartIndex).join('\n');

      const parsed = parseMarkdownTable(tableText);
      if (parsed) {
        return (
          <>
            <div className="mb-2">{headerText}</div>
            <DataTable columns={parsed.columns} rows={parsed.rows} maxHeight={400} />
          </>
        );
      }
    }
  }

  // Default markdown rendering
  return <FormattedMarkdown content={content} />;
}

/**
 * Markdown with custom component renderers
 */
function FormattedMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        code: ({ className, children }) => {
          const match = /language-(\w+)/.exec(className || '');
          const codeString = String(children).replace(/\n$/, '');

          if (match) {
            return <CodeBlock code={codeString} language={match[1]} />;
          }

          return <InlineCode>{codeString}</InlineCode>;
        },
        pre: ({ children }) => <>{children}</>,
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-6 mb-3">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-6 mb-3">{children}</ol>,
        li: ({ children }) => <li className="mb-1">{children}</li>,
        a: ({ href, children }) => (
          <a
            href={href}
            className="text-primary underline underline-offset-2 hover:no-underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        em: ({ children }) => <em className="italic">{children}</em>,
        h1: ({ children }) => <h1 className="text-xl font-bold mb-3">{children}</h1>,
        h2: ({ children }) => <h2 className="text-lg font-bold mb-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-base font-bold mb-2">{children}</h3>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

/**
 * Format query results as a collapsible data table
 */
export interface QueryResultsFormatterProps {
  columns: string[];
  rows: any[][];
  executionTime?: number;
  sql?: string;
}

export function QueryResultsFormatter({ columns, rows, executionTime, sql }: QueryResultsFormatterProps) {
  return (
    <div className="query-results">
      {/* Show SQL if provided */}
      {sql && (
        <CollapsibleSection title="View SQL" icon={<Code size={14} />} defaultExpanded={false}>
          <CodeBlock code={sql} language="sql" />
        </CollapsibleSection>
      )}

      {/* Results table */}
      {rows.length > 0 ? (
        <CollapsibleSection
          title={`Query Results (${rows.length} row${rows.length !== 1 ? 's' : ''})`}
          icon={<Database size={14} />}
          defaultExpanded={rows.length <= 20}
        >
          {executionTime && (
            <div className="text-xs text-muted-foreground mb-2">
              Executed in {executionTime.toFixed(3)}s
            </div>
          )}
          <DataTable columns={columns} rows={rows} />
        </CollapsibleSection>
      ) : (
        <div>
          {executionTime && (
            <div className="text-xs text-muted-foreground mb-2">
              Executed in {executionTime.toFixed(3)}s
            </div>
          )}
          <EmptyDataTable />
        </div>
      )}
    </div>
  );
}

/**
 * Format tool usage information
 */
export interface ToolUsageFormatterProps {
  toolName: string;
  input?: any;
  output?: any;
  error?: string;
}

export function ToolUsageFormatter({ toolName, input, output, error }: ToolUsageFormatterProps) {
  return (
    <div className="tool-usage">
      <div className="flex items-center gap-2 text-sm mb-2">
        <Code size={14} />
        <span className="font-semibold">Tool: {toolName}</span>
      </div>

      {input && (
        <CollapsibleSection title="Input" defaultExpanded={false}>
          <DetailSection label="Parameters" monospace>
            <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(input, null, 2)}</pre>
          </DetailSection>
        </CollapsibleSection>
      )}

      {output && (
        <CollapsibleSection title="Output" defaultExpanded={false}>
          <DetailSection label="Result" monospace>
            <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(output, null, 2)}</pre>
          </DetailSection>
        </CollapsibleSection>
      )}

      {error && (
        <div className="mt-2 p-3 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">
          <strong>Error:</strong> {error}
        </div>
      )}
    </div>
  );
}
