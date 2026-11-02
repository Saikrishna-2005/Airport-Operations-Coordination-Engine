import React from "react";

import {
  CloudRain,
  UserX,
  Clock,
  AlertTriangle,
  Wrench,
  ShieldAlert,
} from "lucide-react";


// ============================================================
// DYNAMIC RISK FACTORS
// ============================================================

export const RiskFactors = ({ factors = [] }) => {

  if (!factors || factors.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-center text-slate-400 text-xs">
        No active risk factors recorded for this flight.
      </div>
    );
  }


  const getCategoryIcon = (category = "") => {

    const cat = category.toLowerCase();

    if (cat.includes("weather")) return CloudRain;

    if (cat.includes("crew")) return UserX;

    if (cat.includes("delay")) return Clock;

    if (cat.includes("maintenance")) return Wrench;

    if (cat.includes("connection")) return ShieldAlert;

    return AlertTriangle;
  };


  const getSeverityBadge = (severity = "LOW") => {

    switch (severity.toUpperCase()) {

      case "CRITICAL":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";

      case "HIGH":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";

      case "MEDIUM":
        return "bg-sky-500/20 text-sky-300 border-sky-500/40";

      default:
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
    }
  };


  const getBarColor = (severity = "LOW") => {

    switch (severity.toUpperCase()) {

      case "CRITICAL":
        return "bg-rose-500";

      case "HIGH":
        return "bg-amber-500";

      case "MEDIUM":
        return "bg-sky-500";

      default:
        return "bg-emerald-500";
    }
  };


  return (
    <div className="space-y-3">

      {factors.map((factor, index) => {

        const Icon = getCategoryIcon(
          factor.category
        );

        const severityBadge = getSeverityBadge(
          factor.severity
        );

        const barColor = getBarColor(
          factor.severity
        );

        const score = Math.max(
          0,
          Math.min(100, Number(factor.score ?? 0))
        );

        return (

          <div
            key={factor.id ?? index}
            className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors"
          >

            <div className="flex items-center justify-between gap-2 mb-2">

              <div className="flex items-center gap-2">

                <div className="p-1.5 rounded-lg bg-slate-800 text-cyan-400">

                  <Icon className="w-4 h-4" />

                </div>

                <span className="font-semibold text-sm text-slate-100">

                  {factor.category ?? "OTHER"}

                </span>

              </div>


              <div className="flex items-center gap-2">

                <span
                  className={`text-[11px] font-bold uppercase px-2 py-0.5 rounded border ${severityBadge}`}
                >
                  {factor.severity ?? "LOW"}
                </span>

                <span className="font-mono text-sm font-bold text-white">

                  {score}/100

                </span>

              </div>

            </div>


            {/* SEVERITY BAR */}

            <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden mb-2">

              <div
                className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                style={{
                  width: `${score}%`,
                }}
              />

            </div>


            {/* DESCRIPTION */}

            <p className="text-xs text-slate-300/90 leading-relaxed">

              {factor.description ?? "No description available."}

            </p>

          </div>

        );

      })}

    </div>
  );
};

export default RiskFactors;