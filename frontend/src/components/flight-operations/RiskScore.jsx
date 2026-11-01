import React from 'react';
import { AlertTriangle, ShieldCheck, AlertCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react';

/**
 * RiskScore Component
 * 
 * Reusable visual indicator for flight operational risk.
 * Supports compact pills, standard badges, and comprehensive circular gauge representations.
 */
export const RiskScore = ({
  score = 0,
  level = 'LOW',
  size = 'md',
  showLabel = true,
  trend = 'steady'
}) => {
  // Normalize score between 0 and 100
  const normalizedScore = Math.max(0, Math.min(100, Math.round(score)));

  // Derive risk tier if level is omitted or inconsistent
  const tier = (level || (
    normalizedScore >= 80 ? 'CRITICAL' :
    normalizedScore >= 60 ? 'HIGH' :
    normalizedScore >= 30 ? 'MEDIUM' : 'LOW'
  )).toUpperCase();

  // Tier color definitions
  const tierConfig = {
    CRITICAL: {
      bg: 'bg-rose-500/15',
      border: 'border-rose-500/40',
      text: 'text-rose-400',
      glow: 'shadow-[0_0_12px_rgba(244,63,94,0.35)]',
      barColor: '#f43f5e',
      icon: AlertTriangle,
      label: 'Critical Risk'
    },
    HIGH: {
      bg: 'bg-amber-500/15',
      border: 'border-amber-500/40',
      text: 'text-amber-400',
      glow: 'shadow-[0_0_12px_rgba(245,158,11,0.25)]',
      barColor: '#f59e0b',
      icon: AlertCircle,
      label: 'High Risk'
    },
    MEDIUM: {
      bg: 'bg-sky-500/15',
      border: 'border-sky-500/40',
      text: 'text-sky-400',
      glow: 'shadow-[0_0_12px_rgba(14,165,233,0.2)]',
      barColor: '#38bdf8',
      icon: AlertCircle,
      label: 'Moderate Risk'
    },
    LOW: {
      bg: 'bg-emerald-500/15',
      border: 'border-emerald-500/40',
      text: 'text-emerald-400',
      glow: 'shadow-[0_0_12px_rgba(16,185,129,0.2)]',
      barColor: '#10b981',
      icon: ShieldCheck,
      label: 'Low / Nominal'
    }
  };

  const config = tierConfig[tier] || tierConfig.LOW;
  const IconComponent = config.icon;

  if (size === 'sm') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold border ${config.bg} ${config.border} ${config.text} ${tier === 'CRITICAL' ? 'radar-beacon' : ''}`}
        title={`Risk Score: ${normalizedScore}/100 (${config.label})`}
      >
        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: config.barColor }}></span>
        <span>{normalizedScore}</span>
        {showLabel && <span className="font-normal opacity-90">{tier}</span>}
      </span>
    );
  }

  if (size === 'gauge') {
    const strokeDashoffset = 100 - normalizedScore;
    return (
      <div className="flex flex-col items-center justify-center p-3 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="relative w-24 h-24 flex items-center justify-center">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
            <path
              className="text-slate-800"
              strokeWidth="3.2"
              stroke="currentColor"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              strokeWidth="3.5"
              strokeDasharray="100, 100"
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              stroke={config.barColor}
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <span className="text-2xl font-bold tracking-tight text-white font-mono">{normalizedScore}</span>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">/ 100</span>
          </div>
        </div>
        {showLabel && (
          <div className="mt-2 text-center">
            <span className={`text-xs font-semibold uppercase tracking-wider ${config.text}`}>
              {config.label}
            </span>
          </div>
        )}
      </div>
    );
  }

  // Standard 'md' / 'lg' card badge
  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${config.bg} ${config.border} ${config.text} ${config.glow}`}
    >
      <IconComponent className={`w-4 h-4 ${tier === 'CRITICAL' ? 'animate-pulse' : ''}`} />
      <div className="flex items-baseline gap-1.5">
        <span className="text-base font-bold font-mono tracking-tight">{normalizedScore}</span>
        <span className="text-xs opacity-75">/100</span>
      </div>
      {showLabel && (
        <span className="text-xs font-semibold tracking-wide uppercase px-1.5 py-0.5 rounded bg-black/25">
          {tier}
        </span>
      )}
      {trend === 'up' && <TrendingUp className="w-3.5 h-3.5 text-rose-400" title="Risk increasing" />}
      {trend === 'down' && <TrendingDown className="w-3.5 h-3.5 text-emerald-400" title="Risk decreasing" />}
      {trend === 'steady' && <Minus className="w-3.5 h-3.5 text-slate-500" title="Risk stable" />}
    </div>
  );
};

export default RiskScore;
