/**
 * DataTable component - displays query results in a scrollable table
 * Handles large datasets with virtualization-ready design
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export interface DataTableProps {
  columns: string[];
  rows: any[][];
  maxHeight?: number;
  showRowNumbers?: boolean;
}

export function DataTable({ columns, rows, maxHeight = 400, showRowNumbers = true }: DataTableProps) {
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const handleSort = (columnIndex: number) => {
    if (sortColumn === columnIndex) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnIndex);
      setSortDirection('asc');
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
      {/* Table info header */}
      <div className="px-4 py-2 bg-muted/30 border-b border-border text-xs text-muted-foreground">
        {rows.length} row{rows.length !== 1 ? 's' : ''} × {columns.length} column{columns.length !== 1 ? 's' : ''}
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
