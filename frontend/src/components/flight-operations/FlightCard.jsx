import React from 'react';
import { Plane, Clock, AlertTriangle, Users, ChevronRight, ArrowRight } from 'lucide-react';
import { RiskScore } from './RiskScore';

/**
 * FlightCard Component
 * 
 * Interactive card displaying flight routing, delay metrics, and risk tier.
 * Clicking activates the flight in the detailed Operations Command Deck.
 */
export const FlightCard = ({
  flight,
  isSelected = false,
  onSelect
}) => {
  if (!flight) return null;

  const {
    flightNumber,
    airline,
    origin,
    destination,
    aircraft,
    delayMinutes = 0,
    delayReason = '',
    riskScore = 0,
    riskLevel = 'LOW',
    status = 'On Time',
    dependencies
  } = flight;

  // Status badge coloring
  const statusStyles = {
    'Critical Risk': 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    'Delayed': 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    'Boarding': 'bg-sky-500/20 text-sky-300 border-sky-500/40',
    'In Flight': 'bg-purple-500/20 text-purple-300 border-purple-500/40',
    'On Time': 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
  };

  const currentStatusStyle = statusStyles[status] || statusStyles['Delayed'];

  return (
    <div
      onClick={() => onSelect && onSelect(flight)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect && onSelect(flight);
        }
      }}
      className={`relative w-full text-left rounded-xl transition-all duration-200 p-4 cursor-pointer group border ${
        isSelected
          ? 'bg-slate-900 border-cyan-400/80 shadow-[0_0_20px_rgba(6,182,212,0.25)] ring-1 ring-cyan-400/50'
          : 'bg-slate-900/60 hover:bg-slate-900/90 border-slate-800/80 hover:border-slate-700 shadow-md'
      }`}
    >
      {/* Top Header: Flight Number, Airline, Status & Risk */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-lg font-bold text-white tracking-wide group-hover:text-cyan-400 transition-colors">
              {flightNumber}
            </span>
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${currentStatusStyle}`}>
              {status}
            </span>
          </div>
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
            <span>{airline}</span>
            <span>•</span>
            <span className="font-mono text-[11px] text-slate-500">{aircraft?.model}</span>
          </div>
        </div>

        {/* Risk Score Pill */}
        <div className="flex-shrink-0">
          <RiskScore score={riskScore} level={riskLevel} size="sm" showLabel={true} />
        </div>
      </div>

      {/* Route & Timing Bar */}
      <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/70 mb-3">
        <div className="flex items-center justify-between">
          {/* Origin */}
          <div className="text-left">
            <div className="text-xl font-bold font-mono text-slate-100">{origin?.code}</div>
            <div className="text-xs text-slate-400">{origin?.name?.split(' ')[0]}</div>
            <div className="text-[11px] font-mono text-slate-300 mt-0.5">
              Sched: {origin?.scheduledTime}
            </div>
          </div>

          {/* Directional Flight Track Line */}
          <div className="flex-1 px-4 flex flex-col items-center">
            <div className="text-[10px] uppercase font-mono text-slate-500 tracking-wider mb-1">
              {delayMinutes > 0 ? `+${delayMinutes}m delay` : 'On Schedule'}
            </div>
            <div className="w-full relative flex items-center justify-center">
              <div className="h-0.5 w-full bg-slate-800 relative">
                {delayMinutes > 0 && (
                  <div className="absolute inset-0 bg-amber-500/40"></div>
                )}
              </div>
              <div className="absolute bg-slate-900 border border-slate-700 p-1 rounded-full text-cyan-400">
                <Plane className="w-3.5 h-3.5 transform rotate-45" />
              </div>
            </div>
            <div className="text-[10px] text-slate-400 font-mono mt-1">
              Gate {origin?.gate} &rarr; Gate {destination?.gate}
            </div>
          </div>

          {/* Destination */}
          <div className="text-right">
            <div className="text-xl font-bold font-mono text-slate-100">{destination?.code}</div>
            <div className="text-xs text-slate-400">{destination?.name?.split(' ')[0]}</div>
            <div className="text-[11px] font-mono text-slate-300 mt-0.5">
              Est: <span className={delayMinutes > 30 ? 'text-amber-400 font-semibold' : ''}>{destination?.estimatedTime}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Primary operational risk summary */}
      {delayReason && (
        <div className="text-xs text-slate-400 bg-slate-950/40 rounded p-2 border border-slate-800/40 mb-3 line-clamp-2">
          <span className="text-slate-300 font-medium">Issue: </span>
          {delayReason}
        </div>
      )}

      {/* Footer Metadata: Delay Badge, Pax, Selector cue */}
      <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/60">
        <div className="flex items-center gap-3">
          {delayMinutes > 0 ? (
            <span className="inline-flex items-center gap-1 font-mono text-amber-400 font-semibold text-xs">
              <Clock className="w-3.5 h-3.5" />
              +{delayMinutes}m
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 font-mono text-emerald-400 text-xs">
              <Clock className="w-3.5 h-3.5" />
              On Time
            </span>
          )}

          {dependencies?.connectingPassengers > 0 && (
            <span className="inline-flex items-center gap-1 font-mono text-slate-400 text-xs" title="Connecting passengers">
              <Users className="w-3.5 h-3.5 text-cyan-400" />
              {dependencies.connectingPassengers} pax
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 text-cyan-400 text-xs font-semibold group-hover:translate-x-0.5 transition-transform">
          <span>{isSelected ? 'Active Deck' : 'Inspect'}</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </div>
      </div>
    </div>
  );
};

export default FlightCard;
