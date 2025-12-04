/**
 * Message component - displays a single chat message with avatar and formatting
 * Based on DeckBot's sophisticated message UI
 */

import type { ReactNode } from 'react';
import { User, Bot, Terminal, Wrench } from 'lucide-react';

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export interface MessageProps {
  role: MessageRole;
  content: string | ReactNode;
  timestamp?: string;
  children?: ReactNode;
}

const ROLE_CONFIG: Record<MessageRole, { icon: any; bgColor: string; textColor: string }> = {
  user: {
    icon: User,
    bgColor: 'hsl(var(--primary))',
    textColor: 'hsl(var(--primary-foreground))',
  },
  assistant: {
    icon: Bot,
    bgColor: 'hsl(var(--secondary))',
    textColor: 'hsl(var(--secondary-foreground))',
  },
  system: {
    icon: Terminal,
    bgColor: 'hsl(var(--muted))',
    textColor: 'hsl(var(--muted-foreground))',
  },
  tool: {
    icon: Wrench,
    bgColor: 'hsl(var(--muted))',
    textColor: 'hsl(var(--muted-foreground))',
  },
};

export function Message({ role, content, timestamp, children }: MessageProps) {
  const config = ROLE_CONFIG[role];
  const Icon = config.icon;

  return (
    <div className="message-container flex gap-4 px-6 py-4 hover:bg-muted/30 border-b border-border/50 animate-fade-in">
      {/* Avatar */}
      <div
        className="message-avatar flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
        style={{ backgroundColor: config.bgColor }}
      >
        <Icon size={16} style={{ color: config.textColor }} />
      </div>

      {/* Content */}
      <div className="message-content flex-1 min-w-0 overflow-hidden">
        <div className="message-body overflow-auto">
          {typeof content === 'string' ? (
            <div className={`text-sm leading-relaxed ${role === 'system' ? 'font-mono text-muted-foreground bg-muted/50 p-3 rounded border-l-3 border-l-muted-foreground' : ''}`}>
              {content}
            </div>
          ) : (
            content
          )}
        </div>
        {children && <div className="message-extras mt-3">{children}</div>}
        {timestamp && (
          <div className="text-xs text-muted-foreground mt-2">{timestamp}</div>
        )}
      </div>
    </div>
  );
}
