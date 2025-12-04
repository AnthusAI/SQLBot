/**
 * CollapsibleSection component - expandable/collapsible content section
 * Based on DeckBot's request details toggle
 */

import { useState } from 'react';
import type { ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';

export interface CollapsibleSectionProps {
  title: string;
  children: ReactNode;
  defaultExpanded?: boolean;
  icon?: ReactNode;
}

export function CollapsibleSection({
  title,
  children,
  defaultExpanded = false,
  icon,
}: CollapsibleSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="collapsible-section my-2">
      {/* Toggle button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground rounded transition-colors w-full text-left"
      >
        <ChevronDown
          size={14}
          className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
        {icon && <span className="flex items-center">{icon}</span>}
        <span className="font-medium">{title}</span>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="collapsible-content mt-2 px-3 py-3 bg-muted/30 rounded border border-border">
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * DetailSection component - for displaying labeled details
 */
export interface DetailSectionProps {
  label: string;
  children: ReactNode;
  monospace?: boolean;
}

export function DetailSection({ label, children, monospace = false }: DetailSectionProps) {
  return (
    <div className="detail-section mb-3 last:mb-0">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className={`text-sm ${monospace ? 'font-mono bg-muted p-2 rounded' : ''}`}>
        {children}
      </div>
    </div>
  );
}
