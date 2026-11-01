import React, { useEffect, useState } from "react";

import {
  Plane,
  AlertTriangle,
  GitCommit,
  Sliders,
  Cpu,
  Sparkles,
} from "lucide-react";

import { RiskScore } from "./RiskScore";
import { RiskFactors } from "./RiskFactors";
import { FlightDependency } from "./FlightDependency";
import { ImpactSimulator } from "./ImpactSimulator";
import { AIRecommendation } from "./AIRecommendation";
import { AgentWorkflow } from "./AgentWorkflow";

import { getFlightRisk } from "../../services/flightApi";


// ============================================================
// FLIGHT RISK PANEL
// ============================================================

export const FlightRiskPanel = ({
  flight,
  onDecisionUpdated,
}) => {
  const [activeTab, setActiveTab] = useState(
    "RISK_ASSESSMENT"
  );

  const [riskData, setRiskData] = useState(null);

  const [riskLoading, setRiskLoading] = useState(false);

  const [riskError, setRiskError] = useState(null);

  const flightId = flight?.id;

  // ============================================================
  // FETCH RISK DATA FROM FASTAPI
  // ============================================================

  useEffect(() => {
    let cancelled = false;

    if (!flightId) {
      setRiskData(null);
      setRiskError(null);
      setRiskLoading(false);
      return;
    }

    const loadRisk = async () => {
      setRiskLoading(true);
      setRiskError(null);
      setRiskData(null);

      try {
        const result = await getFlightRisk(flightId);

        if (!cancelled) {
          setRiskData(result);
        }
      } catch (error) {
        if (!cancelled) {
          setRiskError(
            "Unable to retrieve flight risk data."
          );
        }
      } finally {
        if (!cancelled) {
          setRiskLoading(false);
        }
      }
    };

    loadRisk();

    return () => {
      cancelled = true;
    };
  }, [
    flightId,
    flight?.riskScore,
    flight?.status,
    flight?.delayMinutes,
  ]);


  // ============================================================
  // EMPTY STATE
  // ============================================================

  if (!flight) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-12 bg-slate-900/50 border border-slate-800 rounded-xl text-center">
        <Plane className="w-12 h-12 text-slate-700 mb-3 -rotate-45" />

        <h3 className="text-base font-semibold text-slate-300">
          No Flight Selected
        </h3>

        <p className="text-xs text-slate-500 max-w-sm mt-1">
          Select a flight from the priority queue to view
          its operational risk assessment.
        </p>
      </div>
    );
  }


  // ============================================================
  // FLIGHT DETAILS
  // ============================================================

  const flightNumber = flight.flightNumber;

  const airline = flight.airline;

  const origin = flight.origin ?? {};

  const destination = flight.destination ?? {};

  const delayMinutes = Number(
    flight.delayMinutes ?? 0
  );

  const status = flight.status ?? "UNKNOWN";

  const aircraftType =
    flight.aircraftType ??
    flight.aircraft?.model ??
    "N/A";

  const aircraftRegistration =
    flight.aircraftRegistration ??
    flight.aircraft?.tailNumber ??
    "N/A";

  const riskScore = riskData?.riskScore ?? null;

  const riskLevel = riskData?.riskLevel ?? "LOW";

  const riskFactors = riskData?.riskFactors ?? [];

  const agentWorkflow = flight.agentWorkflow ?? [];

  const formatTime = (value) => {
    if (!value) return "N/A";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "N/A";
    }

    return date.toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    });
  };


  // ============================================================
  // COMPONENT
  // ============================================================

  return (
    <div className="flex flex-col h-full bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">

      {/* FLIGHT HEADER */}

      <div className="bg-slate-950/90 border-b border-slate-800 p-5">

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">

          <div className="space-y-1">

            <div className="flex items-center gap-3">

              <span className="font-mono text-2xl font-black text-white">
                {flightNumber}
              </span>

              <span
                className={`text-xs font-bold px-2.5 py-0.5 rounded border uppercase ${
                  status.toUpperCase() === "DELAYED"
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                    : status.toUpperCase() === "CANCELLED"
                    ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                    : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                }`}
              >
                {status}
              </span>

              <span className="text-xs text-slate-400">
                {airline}
              </span>

            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 font-mono">

              <span>{aircraftType}</span>

              <span>•</span>

              <span>Tail: {aircraftRegistration}</span>

            </div>

          </div>


          {/* ROUTE SUMMARY */}

          <div className="flex items-center gap-6 bg-slate-900/90 border border-slate-800 rounded-lg p-3">

            <div className="text-center">

              <div className="text-lg font-bold font-mono text-white">
                {origin.code ?? "N/A"}
              </div>

              <div className="text-[11px] text-slate-400">
                Terminal {flight.terminal ?? "N/A"}
              </div>

              <div className="text-[10px] text-slate-500">
                Gate {flight.gate ?? "N/A"}
              </div>

            </div>


            <div className="flex flex-col items-center">

              <div
                className={`text-xs font-mono font-bold ${
                  delayMinutes > 0
                    ? "text-amber-400"
                    : "text-emerald-400"
                }`}
              >
                {delayMinutes > 0
                  ? `+${delayMinutes}m delay`
                  : "No recorded delay"}
              </div>

              <div className="w-16 h-0.5 bg-slate-700 my-2" />

              <div className="text-[10px] text-slate-400 font-mono">
                {formatTime(flight.scheduledDeparture)}
                {" → "}
                {formatTime(
                  flight.estimatedArrival ??
                  flight.scheduledArrival
                )}
                {" UTC"}
              </div>

            </div>


            <div className="text-center">

              <div className="text-lg font-bold font-mono text-white">
                {destination.code ?? "N/A"}
              </div>

            </div>

          </div>

        </div>

      </div>


      {/* NAVIGATION TABS */}

      <div className="flex items-center border-b border-slate-800 bg-slate-950/50 px-4 py-2 gap-2 overflow-x-auto">

        {[
          ["RISK_ASSESSMENT", "Risk Assessment"],
          ["SIMULATOR", "Impact Simulator"],
          ["DEPENDENCIES", "Dependencies"],
          ["AI_RECOMMENDATION", "AI Mitigation"],
          ["AGENT_PIPELINE", "Agent Pipeline"],
        ].map(([tab, label]) => (

          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap ${
              activeTab === tab
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {label}
          </button>

        ))}

      </div>


      {/* TAB CONTENT */}

      <div className="flex-1 overflow-y-auto p-5 space-y-5">

        {activeTab === "RISK_ASSESSMENT" && (

          <div className="space-y-5">

            {riskLoading && (
              <div className="text-xs text-cyan-400">
                Loading risk assessment...
              </div>
            )}

            {riskError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                <AlertTriangle className="w-4 h-4" />
                {riskError}
              </div>
            )}

            {!riskLoading && !riskError && riskData && (
              <>
                <RiskScore
                  score={riskScore}
                  level={riskLevel}
                  size="gauge"
                  showLabel={true}
                />

                <div>

                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                    Risk Dimension Diagnostics
                  </h4>

                  <RiskFactors factors={riskFactors} />

                </div>

                <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/50 text-xs text-slate-400">
                  Historical risk trends are not available
                  because risk-score history is not yet
                  stored by the backend.
                </div>
              </>
            )}

          </div>

        )}


        {activeTab === "SIMULATOR" && (
          <ImpactSimulator flight={flight} />
        )}


        {activeTab === "DEPENDENCIES" && (
          <FlightDependency flightId={flight.id} />
        )}


        {activeTab === "AI_RECOMMENDATION" && (
          <AIRecommendation
            flight={flight}
            onActionComplete={onDecisionUpdated}
          />
        )}


        {activeTab === "AGENT_PIPELINE" && (
          <AgentWorkflow workflow={agentWorkflow} />
        )}

      </div>

    </div>
  );
};

export default FlightRiskPanel;