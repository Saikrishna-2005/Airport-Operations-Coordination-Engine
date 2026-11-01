import React from "react";

import {
  Activity,
  AlertTriangle,
  Clock,
  CheckCircle2,
  DollarSign,
  Radio,
  Compass,
} from "lucide-react";


// ============================================================
// DYNAMIC OPERATIONAL PULSE COMPONENT
// ============================================================

export const OperationalPulse = ({
  pulseData,
  isLiveApi = false,
}) => {

  const data = pulseData || {
    totalMonitoredFlights: 0,
    criticalRiskFlights: 0,
    highRiskFlights: 0,
    onTimePercentage: null,
    networkAverageDelayMinutes: 0,
    activeDisruptions: 0,
    proactiveSavingsEst: null,
    hubStatus: {},
  };

  return (

    <div className="w-full bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-md">

      {/* ===================================================== */}
      {/* TOP STATUS BAR */}
      {/* ===================================================== */}

      <div className="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-slate-800/80 text-xs">

        <div className="flex items-center gap-3">

          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-slate-300">

            <span className="relative flex h-2 w-2">

              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  isLiveApi
                    ? "bg-emerald-500"
                    : "bg-cyan-500"
                }`}
              />

            </span>

            <span className="font-medium tracking-wide uppercase">

              {isLiveApi
                ? "FastAPI Database Connected"
                : "Operational Demo Mode"}

            </span>

          </div>

          <div className="hidden sm:flex items-center gap-1.5 text-slate-400">

            <Radio className="w-3.5 h-3.5 text-cyan-400" />

            <span>
              Database Statistics
            </span>

          </div>

        </div>

      </div>


      {/* ===================================================== */}
      {/* PRIMARY KPI GRID */}
      {/* ===================================================== */}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-3">


        {/* MONITORED FLIGHTS */}

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">

          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">

            <span>Monitored Flights</span>

            <Activity className="w-3.5 h-3.5 text-sky-400" />

          </div>

          <div className="text-xl font-bold font-mono text-white">

            {data.totalMonitoredFlights}

          </div>

          <div className="text-[11px] text-slate-500 mt-0.5">

            Flights stored in database

          </div>

        </div>


        {/* CRITICAL RISK */}

        <div className="bg-rose-950/20 border border-rose-900/40 rounded-lg p-3">

          <div className="flex items-center justify-between text-rose-300 text-xs mb-1">

            <span className="font-semibold">
              Critical Risk
            </span>

            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />

          </div>

          <div className="text-xl font-bold font-mono text-rose-400">

            {data.criticalRiskFlights}

          </div>

          <div className="text-[11px] text-rose-300/70 mt-0.5">

            Risk score 75 or above

          </div>

        </div>


        {/* HIGH RISK */}

        <div className="bg-amber-950/20 border border-amber-900/40 rounded-lg p-3">

          <div className="flex items-center justify-between text-amber-300 text-xs mb-1">

            <span className="font-semibold">
              High Watch
            </span>

            <Clock className="w-3.5 h-3.5 text-amber-400" />

          </div>

          <div className="text-xl font-bold font-mono text-amber-400">

            {data.highRiskFlights}

          </div>

          <div className="text-[11px] text-amber-300/70 mt-0.5">

            Risk score 50–74

          </div>

        </div>


        {/* ON-TIME PERFORMANCE */}

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">

          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">

            <span>On-Time Rate</span>

            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />

          </div>

          <div className="text-xl font-bold font-mono text-emerald-400">

            {data.onTimePercentage === null
              ? "N/A"
              : `${data.onTimePercentage}%`}

          </div>

          <div className="text-[11px] text-slate-500 mt-0.5">

            Recorded delay ≤ 15 minutes

          </div>

        </div>


        {/* AVERAGE NETWORK DELAY */}

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">

          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">

            <span>Avg Network Delay</span>

            <Compass className="w-3.5 h-3.5 text-purple-400" />

          </div>

          <div className="text-xl font-bold font-mono text-purple-300">

            +{data.networkAverageDelayMinutes}m

          </div>

          <div className="text-[11px] text-slate-500 mt-0.5">

            Average recorded departure delay

          </div>

        </div>


        {/* COST AVOIDED */}

        <div className="bg-emerald-950/20 border border-emerald-900/40 rounded-lg p-3">

          <div className="flex items-center justify-between text-emerald-300 text-xs mb-1">

            <span className="font-semibold">
              Cost Avoided
            </span>

            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />

          </div>

          <div className="text-xl font-bold font-mono text-emerald-400">

            {data.proactiveSavingsEst ?? "N/A"}

          </div>

          <div className="text-[11px] text-emerald-300/70 mt-0.5">

            Financial model not connected

          </div>

        </div>

      </div>

    </div>

  );

};

export default OperationalPulse;