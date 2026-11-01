import React from 'react';
import { Search, Filter, X, ArrowUpDown, SlidersHorizontal } from 'lucide-react';

/**
 * SearchFilter Component
 * 
 * Multi-dimensional filtering and search control for the Flight Priority Board.
 * Reusable across any flight search or dispatch roster.
 */
export const SearchFilter = ({
  searchTerm = '',
  onSearchChange,
  riskFilter = 'ALL',
  onRiskFilterChange,
  statusFilter = 'ALL',
  onStatusFilterChange,
  sortBy = 'risk',
  onSortChange,
  onResetFilters,
  resultCount = 0,
  totalCount = 0
}) => {
  const isFiltered = searchTerm !== '' || riskFilter !== 'ALL' || statusFilter !== 'ALL';

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        {/* Search Input Box */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search flight number, airline, or route (e.g. AA-1042, JFK, LHR)..."
            className="w-full bg-slate-950/80 border border-slate-700/80 rounded-lg pl-9 pr-8 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 transition-all font-mono"
          />
          {searchTerm && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              title="Clear search"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Filter and Sort Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Risk Level Filter */}
          <div className="flex items-center gap-1.5 bg-slate-950/70 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs">
            <span className="text-slate-400 font-medium flex items-center gap-1">
              <Filter className="w-3 h-3 text-cyan-400" />
              Risk:
            </span>
            <select
              value={riskFilter}
              onChange={(e) => onRiskFilterChange(e.target.value)}
              className="bg-transparent text-slate-200 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900 text-slate-200">All Levels</option>
              <option value="CRITICAL" className="bg-slate-900 text-rose-400">Critical (&ge; 80)</option>
              <option value="HIGH" className="bg-slate-900 text-amber-400">High (60-79)</option>
              <option value="MEDIUM" className="bg-slate-900 text-sky-400">Medium (30-59)</option>
              <option value="LOW" className="bg-slate-900 text-emerald-400">Low (&lt; 30)</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5 bg-slate-950/70 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs">
            <span className="text-slate-400 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => onStatusFilterChange(e.target.value)}
              className="bg-transparent text-slate-200 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900 text-slate-200">All Statuses</option>
              <option value="Critical Risk" className="bg-slate-900 text-rose-400">Critical Risk</option>
              <option value="Delayed" className="bg-slate-900 text-amber-400">Delayed</option>
              <option value="Boarding" className="bg-slate-900 text-sky-400">Boarding</option>
              <option value="In Flight" className="bg-slate-900 text-purple-400">In Flight</option>
              <option value="On Time" className="bg-slate-900 text-emerald-400">On Time</option>
            </select>
          </div>

          {/* Sort Control */}
          <div className="flex items-center gap-1.5 bg-slate-950/70 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs">
            <span className="text-slate-400 font-medium flex items-center gap-1">
              <ArrowUpDown className="w-3 h-3 text-cyan-400" />
              Sort:
            </span>
            <select
              value={sortBy}
              onChange={(e) => onSortChange(e.target.value)}
              className="bg-transparent text-slate-200 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="risk" className="bg-slate-900 text-slate-200">Highest Risk</option>
              <option value="delay" className="bg-slate-900 text-slate-200">Longest Delay</option>
              <option value="flightNumber" className="bg-slate-900 text-slate-200">Flight No.</option>
            </select>
          </div>

          {/* Reset button */}
          {isFiltered && (
            <button
              onClick={onResetFilters}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs transition-colors"
              title="Reset all search filters"
            >
              <X className="w-3 h-3" />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Result counter metadata line */}
      <div className="flex items-center justify-between text-xs text-slate-400 mt-2.5 pt-2 border-t border-slate-800/60">
        <span className="font-mono">
          Showing <span className="font-bold text-white">{resultCount}</span> of{' '}
          <span className="text-slate-300">{totalCount}</span> flights
        </span>
        {isFiltered && (
          <span className="text-cyan-400 text-[11px]">
            Filtered View Active
          </span>
        )}
      </div>
    </div>
  );
};

export default SearchFilter;
