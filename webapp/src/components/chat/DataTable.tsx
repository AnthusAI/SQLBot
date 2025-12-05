/**
 * DataTable component - displays query results in a scrollable table
 * Handles large datasets with virtualization-ready design
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, Download, FileSpreadsheet, FileType, Database } from 'lucide-react';

export interface DataTableProps {
  columns: string[];
  rows: any[][];
  maxHeight?: number;
  showRowNumbers?: boolean;
  sessionId?: string;
  queryIndex?: number;
}

export function DataTable({ columns, rows, maxHeight = 400, showRowNumbers = true, sessionId, queryIndex }: DataTableProps) {
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [showExportMenu, setShowExportMenu] = useState(false);

  const handleSort = (columnIndex: number) => {
    if (sortColumn === columnIndex) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnIndex);
      setSortDirection('asc');
    }
  };

  const handleExport = async (format: 'csv' | 'excel' | 'parquet' | 'hdf5') => {
    if (!sessionId || !queryIndex) {
      console.error('Cannot export: missing sessionId or queryIndex');
      return;
    }

    setShowExportMenu(false);

    try {
      const url = `/api/sessions/${sessionId}/query_results/${queryIndex}/export/${format}`;

      // Trigger browser download
      const link = document.createElement('a');
      link.href = url;
      link.download = `query_${queryIndex}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const sortedRows = sortColumn !== null
    ? [...rows].sort((a, b) => {
        const aVal = a[sortColumn];
        const bVal = b[sortColumn];
        const compare = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        return sortDirection === 'asc' ? compare : -compare;
      })
    : rows;

  return (
    <div className="data-table-container my-3 border border-border rounded-md overflow-hidden max-w-full">
      {/* Table info header with export button */}
      <div className="px-4 py-2 bg-muted/30 border-b border-border text-xs text-muted-foreground flex items-center justify-between">
        <span>
          {rows.length} row{rows.length !== 1 ? 's' : ''} × {columns.length} column{columns.length !== 1 ? 's' : ''}
        </span>

        {/* Export dropdown - only show if we have session context */}
        {sessionId && queryIndex && (
          <div className="relative" style={{ position: 'relative' }}>
            <button
              onClick={(e) => {
                setShowExportMenu(!showExportMenu);
                // Store button position for dropdown positioning
                const rect = e.currentTarget.getBoundingClientRect();
                (e.currentTarget as any).dataset.x = rect.left.toString();
                (e.currentTarget as any).dataset.y = rect.bottom.toString();
              }}
              className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-foreground hover:bg-accent rounded transition-colors"
              title="Export data"
              ref={(el) => {
                if (el && showExportMenu) {
                  const rect = el.getBoundingClientRect();
                  el.dataset.x = rect.right.toString();
                  el.dataset.y = rect.bottom.toString();
                }
              }}
            >
              <Download size={14} />
              Export
            </button>

            {showExportMenu && (
              <>
                {/* Overlay to close menu */}
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowExportMenu(false)}
                />

                {/* Dropdown menu - positioned with fixed positioning to escape overflow */}
                <div
                  className="dropdown-menu"
                  style={{
                    display: 'block',
                    position: 'fixed',
                    zIndex: 20,
                    top: document.querySelector('[title="Export data"]')?.getBoundingClientRect().bottom + 'px' || '0',
                    right: (window.innerWidth - (document.querySelector('[title="Export data"]')?.getBoundingClientRect().right || 0)) + 'px',
                    width: 'max-content',
                    maxWidth: '200px',
                    left: 'auto'
                  }}
                >
                  <div style={{ padding: '8px 12px', fontSize: '11px', fontWeight: 600, color: 'hsl(var(--muted-foreground))', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Download as
                  </div>
                  <div className="dropdown-divider" />
                  <button
                    onClick={() => handleExport('csv')}
                    className="dropdown-item"
                  >
                    <FileType size={16} />
                    CSV
                  </button>
                  <button
                    onClick={() => handleExport('excel')}
                    className="dropdown-item"
                  >
                    <FileSpreadsheet size={16} />
                    Excel
                  </button>
                  <button
                    onClick={() => handleExport('parquet')}
                    className="dropdown-item"
                  >
                    <Database size={16} />
                    Parquet
                  </button>
                  <button
                    onClick={() => handleExport('hdf5')}
                    className="dropdown-item"
                  >
                    <Database size={16} />
                    HDF5
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Scrollable table - both vertical and horizontal */}
      <div
        className="overflow-auto"
        style={{ maxHeight: `${maxHeight}px`, maxWidth: '100%' }}
      >
        <table className="text-sm" style={{ minWidth: '100%', width: 'max-content' }}>
          <thead className="sticky top-0 bg-muted z-10">
            <tr>
              {showRowNumbers && (
                <th className="px-4 py-2 text-left font-semibold text-muted-foreground border-b border-border w-12">
                  #
                </th>
              )}
              {columns.map((column, idx) => (
                <th
                  key={idx}
                  className="px-4 py-2 text-left font-semibold border-b border-border cursor-pointer hover:bg-accent transition-colors"
                  onClick={() => handleSort(idx)}
                >
                  <div className="flex items-center gap-2">
                    <span>{column}</span>
                    {sortColumn === idx && (
                      sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className="hover:bg-muted/20 transition-colors border-b border-border/50 last:border-b-0"
              >
                {showRowNumbers && (
                  <td className="px-4 py-2 text-muted-foreground font-mono text-xs">
                    {rowIdx + 1}
                  </td>
                )}
                {row.map((cell, cellIdx) => (
                  <td key={cellIdx} className="px-4 py-2">
                    {cell === null ? (
                      <span className="text-muted-foreground italic">null</span>
                    ) : typeof cell === 'boolean' ? (
                      <span className={cell ? 'text-green-600' : 'text-red-600'}>
                        {cell.toString()}
                      </span>
                    ) : typeof cell === 'number' ? (
                      <span className="font-mono">{cell}</span>
                    ) : (
                      <span>{String(cell)}</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * EmptyDataTable component - shown when no results
 */
export function EmptyDataTable() {
  return (
    <div className="data-table-container my-3 border border-border rounded-md overflow-hidden">
      <div className="px-4 py-8 text-center text-muted-foreground">
        <p className="text-sm">No results to display</p>
      </div>
    </div>
  );
}
