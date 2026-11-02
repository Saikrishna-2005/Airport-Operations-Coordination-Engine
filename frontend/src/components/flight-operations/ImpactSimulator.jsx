import React, { useState, useEffect } from "react";
import {
  Sliders,
  RotateCcw,
  AlertTriangle,
  Clock,
  GitBranch,
  ShieldAlert,
  Loader2,
} from "lucide-react";

import { simulateFlightImpact } from "../../services/flightApi";

/**
 * ImpactSimulator
 *
 * Uses the real FastAPI impact simulation endpoint.
 * Flight IDs are numeric SQLite IDs, not flight numbers.
 */

export const ImpactSimulator = ({
  flight,
  onSimulationChange,
}) => {
  const [additionalDelay, setAdditionalDelay] = useState(0);
  const [simulationResult, setSimulationResult] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationError, setSimulationError] = useState("");

  const flightId = flight?.id;
  const flightNumber =
    flight?.flightNumber ?? flight?.flight_number ?? "Unknown";

  const presetIncrements = [15, 30, 45, 60, 90, 120];

  useEffect(() => {
    let cancelled = false;

    const runSimulation = async () => {
      setSimulationResult(null);
      setSimulationError("");

      if (!Number.isInteger(Number(flightId)) || Number(flightId) <= 0) {
        setIsSimulating(false);
        return;
      }

      setIsSimulating(true);

      try {
        const result = await simulateFlightImpact(
          Number(flightId),
          additionalDelay
        );

        if (!cancelled) {
          setSimulationResult(result);
        }
      } catch (error) {
        if (!cancelled) {
          const message =
            error?.response?.data?.detail ||
            error?.message ||
            "Impact simulation failed.";

          setSimulationError(
            typeof message === "string"
              ? message
              : JSON.stringify(message)
          );
        }
      } finally {
        if (!cancelled) {
          setIsSimulating(false);
        }
      }
    };

    runSimulation();

    return () => {
      cancelled = true;
    };
  }, [flightId, additionalDelay]);

  useEffect(() => {
    if (simulationResult && onSimulationChange) {
      onSimulationChange(simulationResult);
    }
  }, [simulationResult, onSimulationChange]);

  const handleReset = () => {
    setAdditionalDelay(0);
  };

  // Support snake_case FastAPI responses and any existing
  // camelCase fields without fabricating missing metrics.
  const getField = (...names) => {
    if (!simulationResult) return null;

    for (const name of names) {
      const value = simulationResult[name];

      if (value !== undefined && value !== null) {
        return value;
      }
    }

    return null;
  };

  const formatMinutes = (value) => {
    if (value === null || value === undefined) return "N/A";

    const number = Number(value);
    return Number.isFinite(number) ? `${number} min` : "N/A";
  };

  const formatScore = (value) => {
    if (value === null || value === undefined) return "N/A";

    const number = Number(value);
    return Number.isFinite(number) ? `${number}/100` : "N/A";
  };

  const baselineDelay = getField(
    "baseline_delay_minutes",
    "baselineDelayMinutes",
    "current_delay_minutes",
    "currentDelayMinutes"
  );

  const projectedDelay = getField(
    "projected_total_delay_minutes",
    "projectedTotalDelayMinutes",
    "projected_delay_minutes",
    "projectedDelayMinutes"
  );

  const projectedRisk = getField(
    "simulated_risk_score",
    "simulatedRiskScore",
    "projected_risk_score",
    "projectedRiskScore"
  );

  const riskDelta = getField("risk_delta", "riskDelta");

  const riskLevel = getField(
    "simulated_risk_level",
    "simulatedRiskLevel",
    "risk_level",
    "riskLevel"
  );

  const affectedFlights = getField(
    "affected_flights",
    "affectedFlights",
    "impacted_flights",
    "impactedFlights",
    "dependency_impacts",
    "dependencyImpacts"
  );

  const affectedFlightCount = Array.isArray(affectedFlights)
    ? affectedFlights.length
    : getField(
        "affected_flight_count",
        "affectedFlightCount",
        "impacted_flights_count",
        "impactedFlightsCount"
      );

  const curfewRisk = getField("curfew_risk", "curfewRisk");

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Sliders className="w-4 h-4" />
          </div>

          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              What-If Impact Simulator
            </h3>

            <p className="text-xs text-slate-400">
              Simulate departure delays using live backend data
            </p>

            <p className="text-xs text-cyan-400 mt-1">
              Flight: {flightNumber} | ID: {flightId ?? "N/A"}
            </p>
          </div>
        </div>

        {additionalDelay > 0 && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
        )}
      </div>

      {/* Delay Controls */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-300">
            Simulate Additional Delay:
          </label>

          <span className="font-mono text-base font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded">
            +{additionalDelay} min
          </span>
        </div>

        <input
          type="range"
          min="0"
          max="120"
          step="5"
          value={additionalDelay}
          onChange={(event) =>
            setAdditionalDelay(Number(event.target.value))
          }
          className="w-full h-2 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-cyan-400"
        />

        <div className="grid grid-cols-6 gap-1.5 pt-1">
          {presetIncrements.map((minutes) => (
            <button
              key={minutes}
              onClick={() => setAdditionalDelay(minutes)}
              className={`py-1 text-xs font-mono rounded border transition-colors ${
                additionalDelay === minutes
                  ? "bg-cyan-500/30 border-cyan-400 text-cyan-200 font-bold"
                  : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
              }`}
            >
              +{minutes}m
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {isSimulating && (
        <div className="flex items-center gap-2 text-cyan-400 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Calculating impact using FastAPI...
        </div>
      )}

      {/* Error */}
      {simulationError && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30">
          <AlertTriangle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />

          <div>
            <p className="text-sm font-semibold text-rose-300">
              Simulation Failed
            </p>

            <p className="text-xs text-rose-200 mt-1">
              {simulationError}
            </p>
          </div>
        </div>
      )}

      {/* Results */}
      {simulationResult && !isSimulating && (
        <div className="space-y-3 pt-2">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Total Delay */}
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
                <span>Total Delay</span>
                <Clock className="w-3.5 h-3.5 text-amber-400" />
              </div>

              <div className="text-lg font-bold font-mono text-white">
                {formatMinutes(projectedDelay)}
              </div>

              <div className="text-[11px] font-mono text-amber-400 mt-0.5">
                Baseline: {formatMinutes(baselineDelay)}
              </div>
            </div>

            {/* Risk Score */}
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
                <span>Projected Risk</span>
                <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              </div>

              <div className="text-lg font-bold font-mono text-white">
                {formatScore(projectedRisk)}
              </div>

              <div className="text-[11px] font-mono text-rose-400 mt-0.5">
                {riskDelta !== null
                  ? `${Number(riskDelta) > 0 ? "+" : ""}${riskDelta} pts`
                  : riskLevel ?? "Risk change unavailable"}
              </div>
            </div>

            {/* Downstream Flights */}
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
                <span>Affected Flights</span>
                <GitBranch className="w-3.5 h-3.5 text-sky-400" />
              </div>

              <div className="text-lg font-bold font-mono text-white">
                {affectedFlightCount ?? "N/A"}
              </div>

              <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                Downstream dependencies
              </div>
            </div>

            {/* Added Delay */}
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
                <span>Added Delay</span>
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
              </div>

              <div className="text-lg font-bold font-mono text-white">
                +{additionalDelay}m
              </div>

              <div className="text-[11px] font-mono text-cyan-400 mt-0.5">
                What-if scenario
              </div>
            </div>
          </div>

          {/* Downstream Flight Details */}
          {Array.isArray(affectedFlights) &&
            affectedFlights.length > 0 && (
              <div className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400 mb-3">
                  Downstream Flight Impacts
                </h4>

                <div className="space-y-2">
                  {affectedFlights.map((affectedFlight, index) => {
                    const number =
                      affectedFlight.flight_number ??
                      affectedFlight.dependent_flight_number ??
                      affectedFlight.flightNumber ??
                      affectedFlight.dependentFlightNumber ??
                      null;

                    const id =
                      affectedFlight.flight_id ??
                      affectedFlight.dependent_flight_id ??
                      affectedFlight.flightId ??
                      affectedFlight.dependentFlightId ??
                      null;

                    const delay =
                      affectedFlight.propagated_delay_minutes ??
                      affectedFlight.propagatedDelayMinutes ??
                      affectedFlight.additional_delay_minutes ??
                      affectedFlight.additionalDelayMinutes ??
                      null;

                    return (
                      <div
                        key={id ?? index}
                        className="flex items-center justify-between gap-3 rounded border border-slate-800 bg-slate-900/80 p-3"
                      >
                        <div>
                          <p className="text-sm font-semibold text-white">
                            {number ?? (id != null ? `Flight ID: ${id}` : `Affected flight ${index + 1}`)}
                          </p>

                          {id != null && number != null && (
                            <p className="text-xs text-slate-400">
                              ID: {id}
                            </p>
                          )}
                        </div>

                        <span className="text-xs font-mono text-amber-400">
                          {delay != null
                            ? `+${delay} min`
                            : "Impact recorded"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

          {/* Curfew Warning */}
          {curfewRisk === true && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />

              <div className="text-xs text-rose-300">
                <span className="font-bold">
                  Curfew Risk Warning:
                </span>{" "}
                The simulation reports a potential curfew risk.
                Review the affected flight and airport constraints.
              </div>
            </div>
          )}

          <p className="text-[11px] text-slate-500">
            Results are provided by the FastAPI impact simulation
            endpoint. Unavailable metrics are displayed as N/A.
          </p>
        </div>
      )}
    </div>
  );
};

export default ImpactSimulator;