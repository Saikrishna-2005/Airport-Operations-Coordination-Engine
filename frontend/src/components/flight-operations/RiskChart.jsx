import React from 'react';
import { TrendingUp, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';

/**
 * RiskChart Component
 * 
 * Interactive SVG visual trajectory illustrating risk escalation and delay progression
 * across dispatch timeline intervals (T-120m to Current Operations).
 */
export const RiskChart = ({ data = [] }) => {
  if (!data || data.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-center text-slate-400 text-xs">
        No historical trend telemetry recorded.
      </div>
    );
  }

  // Dimensions for SVG canvas
  const width = 500;
  const height = 180;
  const padding = { top: 20, right: 30, bottom: 30, left: 40 };

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Scale calculations
  const maxScore = 100;
  const pointsCount = data.length;

  const points = data.map((d, index) => {
    const x = padding.left + (index / (pointsCount - 1 || 1)) * chartWidth;
    const y = padding.top + chartHeight - (d.score / maxScore) * chartHeight;
    return { ...d, x, y };
  });

  // Generate SVG path for line
  const linePath = points.reduce((acc, point, index) => {
    return index === 0 ? `M ${point.x} ${point.y}` : `${acc} L ${point.x} ${point.y}`;
  }, '');

  // Generate SVG area path for gradient fill
  const areaPath = points.length > 0
    ? `${linePath} L ${points[points.length - 1].x} ${padding.top + chartHeight} L ${points[0].x} ${padding.top + chartHeight} Z`
    : '';

  // Critical threshold Y position (score = 80)
  const criticalY = padding.top + chartHeight - (80 / maxScore) * chartHeight;
  // Warning threshold Y position (score = 60)
  const warningY = padding.top + chartHeight - (60 / maxScore) * chartHeight;

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-cyan-400" />
          <h4 className="text-xs font-bold text-white uppercase tracking-wider">
            Risk & Delay Trajectory (T-120m to Present)
          </h4>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono">
          <span className="flex items-center gap-1 text-rose-400">
            <span className="w-2 h-0.5 bg-rose-500 inline-block"></span>
            Critical (&ge;80)
          </span>
          <span className="flex items-center gap-1 text-cyan-400">
            <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block"></span>
            Risk Score
          </span>
        </div>
      </div>

      {/* SVG Line Graph */}
      <div className="w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible select-none"
        >
          <defs>
            <linearGradient id="riskAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines and score labels */}
          {[0, 20, 40, 60, 80, 100].map((score) => {
            const y = padding.top + chartHeight - (score / maxScore) * chartHeight;
            return (
              <g key={score}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="#1e293b"
                  strokeWidth="1"
                  strokeDasharray={score === 0 ? 'none' : '3 3'}
                />
                <text
                  x={padding.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="9"
                  fill="#64748b"
                  fontFamily="monospace"
                >
                  {score}
                </text>
              </g>
            );
          })}

          {/* Critical Threshold Line */}
          <line
            x1={padding.left}
            y1={criticalY}
            x2={width - padding.right}
            y2={criticalY}
            stroke="#f43f5e"
            strokeWidth="1"
            strokeDasharray="4 4"
            opacity="0.8"
          />

          {/* Warning Threshold Line */}
          <line
            x1={padding.left}
            y1={warningY}
            x2={width - padding.right}
            y2={warningY}
            stroke="#f59e0b"
            strokeWidth="1"
            strokeDasharray="4 4"
            opacity="0.5"
          />

          {/* Area fill */}
          {areaPath && (
            <path d={areaPath} fill="url(#riskAreaGradient)" />
          )}

          {/* Trend line */}
          {linePath && (
            <path
              d={linePath}
              fill="none"
              stroke="#22d3ee"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Data Points */}
          {points.map((point, index) => {
            const isLatest = index === points.length - 1;
            return (
              <g key={index} className="cursor-pointer group">
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={isLatest ? 4.5 : 3}
                  fill={isLatest ? '#f43f5e' : '#0891b2'}
                  stroke="#ffffff"
                  strokeWidth={isLatest ? '2' : '1.5'}
                />

                {/* Score value above point */}
                <text
                  x={point.x}
                  y={point.y - 7}
                  textAnchor="middle"
                  fontSize="10"
                  fontWeight="bold"
                  fill={isLatest ? '#f43f5e' : '#e2e8f0'}
                  fontFamily="monospace"
                >
                  {point.score}
                </text>

                {/* Timeline X Axis Label */}
                <text
                  x={point.x}
                  y={height - 10}
                  textAnchor="middle"
                  fontSize="10"
                  fill="#94a3b8"
                  fontFamily="monospace"
                >
                  {point.time}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Delay Progression Indicator Footer */}
      <div className="grid grid-cols-5 gap-2 pt-2 border-t border-slate-800/80">
        {data.map((item, idx) => (
          <div key={idx} className="text-center bg-slate-950/60 p-1.5 rounded border border-slate-800/60">
            <div className="text-[10px] text-slate-500 font-mono">{item.time}</div>
            <div className={`text-xs font-mono font-bold ${item.delay > 60 ? 'text-rose-400' : item.delay > 30 ? 'text-amber-400' : 'text-slate-300'}`}>
              +{item.delay}m
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RiskChart;
