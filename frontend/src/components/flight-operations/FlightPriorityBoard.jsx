import React, { useState } from 'react';
import { Plane, AlertTriangle, ShieldCheck, Clock, Layers } from 'lucide-react';
import { FlightCard } from './FlightCard';

/**
 * FlightPriorityBoard Component
 * 
 * Orchestrates the dispatch priority queue. Categorizes flights into
 * actionable triage groups: Critical Escalations, High Delay Watch, and Nominal Flights.
 */
export const FlightPriorityBoard = ({
  flights = [],
  selectedFlightId = null,
  onSelectFlight,
  isLoading = false
}) => {
  const [activeTab, setActiveTab] = useState('ALL');

  // Compute category counts
  const criticalCount = flights.filter(f => f.riskScore >= 80 || f.priority === 'CRITICAL').length;
  const highWatchCount = flights.filter(f => (f.riskScore >= 60 && f.riskScore < 80) || (f.delayMinutes >= 60 && f.riskScore < 80)).length;
  const nominalCount = flights.filter(f => f.riskScore < 60 && f.delayMinutes < 60).length;

  // Filter based on active board tab
  const displayedFlights = flights.filter(f => {
    if (activeTab === 'CRITICAL') return f.riskScore >= 80 || f.priority === 'CRITICAL';
    if (activeTab === 'HIGH_WATCH') return (f.riskScore >= 60 && f.riskScore < 80) || (f.delayMinutes >= 60 && f.riskScore < 80);
    if (activeTab === 'NOMINAL') return f.riskScore < 60 && f.delayMinutes < 60;
    return true; // ALL
  });

  return (
    <div className="flex flex-col h-full bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      {/* Category Triage Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/70 p-2 overflow-x-auto gap-1">
        <button
          onClick={() => setActiveTab('ALL')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
            activeTab === 'ALL'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>All Priority</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-300">
            {flights.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('CRITICAL')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
            activeTab === 'CRITICAL'
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm'
              : 'text-slate-400 hover:text-rose-400 hover:bg-slate-800/50'
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
          <span>Critical</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-rose-950/80 text-rose-300 border border-rose-800/60">
            {criticalCount}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('HIGH_WATCH')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
            activeTab === 'HIGH_WATCH'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
              : 'text-slate-400 hover:text-amber-400 hover:bg-slate-800/50'
          }`}
        >
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span>Delay Watch</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-950/80 text-amber-300 border border-amber-800/60">
            {highWatchCount}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('NOMINAL')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
            activeTab === 'NOMINAL'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
              : 'text-slate-400 hover:text-emerald-400 hover:bg-slate-800/50'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Nominal</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
            {nominalCount}
          </span>
        </button>
      </div>

      {/* Flight Cards Feed */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 max-h-[750px]">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-400 space-y-3">
            <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm">Polling flight operations telemetry...</p>
          </div>
        ) : displayedFlights.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-400 border border-dashed border-slate-800 rounded-xl">
            <Plane className="w-10 h-10 text-slate-600 mb-2 transform -rotate-45" />
            <h4 className="text-sm font-semibold text-slate-300">No Flights in this category</h4>
            <p className="text-xs text-slate-500 mt-1 text-center">
              Try adjusting your search criteria or triage tab filters.
            </p>
          </div>
        ) : (
          displayedFlights.map((flight) => (
            <FlightCard
              key={flight.id || flight.flightNumber}
              flight={flight}
              isSelected={selectedFlightId === (flight.id || flight.flightNumber)}
              onSelect={onSelectFlight}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default FlightPriorityBoard;
