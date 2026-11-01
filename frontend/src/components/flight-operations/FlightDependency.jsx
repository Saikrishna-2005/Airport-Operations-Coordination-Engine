import React, { useEffect, useState } from "react";

import {
  GitCommit,
  ArrowDownRight,
  Users,
  Clock,
  AlertCircle,
  UserCheck,
  RefreshCw,
} from "lucide-react";

import { getFlightDependencies } from "../../services/flightApi";

// ============================================================
// DYNAMIC FLIGHT DEPENDENCY COMPONENT
// ============================================================

export const FlightDependency = ({ flightId }) => {
  const [dependencies, setDependencies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    if (!flightId) {
      setDependencies([]);
      setError(null);
      return;
    }

    const loadDependencies = async () => {
      setLoading(true);
      setError(null);
      setDependencies([]);

      try {
        const result = await getFlightDependencies(flightId);

        if (!cancelled) {
          setDependencies(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError("Unable to load flight dependencies.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadDependencies();

    return () => {
      cancelled = true;
    };
  }, [flightId]);

  const aircraftDependencies = dependencies.filter(
    (item) => item.dependencyType === "AIRCRAFT"
  );

  const crewDependencies = dependencies.filter(
    (item) => item.dependencyType === "CREW"
  );

  const passengerDependencies = dependencies.filter(
    (item) => item.dependencyType === "PASSENGER_CONNECTION"
  );

  const gateDependencies = dependencies.filter(
    (item) => item.dependencyType === "GATE"
  );

  const getStatusColor = (status = "") => {
    const normalized = status.toUpperCase();

    if (
      normalized === "CANCELLED" ||
      normalized === "DIVERTED"
    ) {
      return "bg-rose-500/20 text-rose-300 border-rose-500/40";
    }

    if (normalized === "DELAYED") {
      return "bg-amber-500/20 text-amber-300 border-amber-500/40";
    }

    return "bg-slate-800 text-slate-300 border-slate-700";
  };

  const renderDependency = (dependency) => (
    <div
      key={dependency.id}
      className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800/70"
    >
      <div className="flex items-center gap-2">
        <ArrowDownRight className="w-4 h-4 text-cyan-400" />

        <div>
          <div className="font-mono text-sm font-semibold text-white">
            {dependency.dependentFlightNumber}
          </div>

          <div className="text-[11px] text-slate-500">
            Flight ID: {dependency.dependentFlightId}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {dependency.dependencyType === "AIRCRAFT" && (
          <span className="text-xs font-mono text-cyan-300">
            {dependency.minimumTurnaroundMinutes} min turnaround
          </span>
        )}

        <span
          className={`px-2 py-0.5 rounded border text-[10px] font-bold uppercase ${getStatusColor(
            dependency.dependentFlightStatus
          )}`}
        >
          {dependency.dependentFlightStatus}
        </span>
      </div>
    </div>
  );

  if (!flightId) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-center text-slate-400 text-xs">
        Select a flight to view its dependencies.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 p-6 text-cyan-400 text-xs">
        <RefreshCw className="w-4 h-4 animate-spin" />
        Loading dependencies from FastAPI...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
        <AlertCircle className="w-4 h-4" />
        {error}
      </div>
    );
  }

  if (dependencies.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-center text-slate-400 text-xs">
        No dependencies are recorded for this flight.
      </div>
    );
  }

  return (
    <div className="space-y-4">

      {/* AIRCRAFT DEPENDENCIES */}

      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <GitCommit className="w-4 h-4 text-cyan-400" />

            <h4 className="text-xs font-bold text-slate-200 uppercase">
              Downstream Aircraft Dependencies
            </h4>
          </div>

          <span className="text-xs text-cyan-300 font-mono">
            {aircraftDependencies.length} linked
          </span>
        </div>

        {aircraftDependencies.length === 0 ? (
          <p className="text-xs text-slate-500">
            No aircraft dependencies recorded.
          </p>
        ) : (
          <div className="space-y-2">
            {aircraftDependencies.map(renderDependency)}
          </div>
        )}
      </div>

      {/* PASSENGER CONNECTIONS */}

      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center gap-2 mb-3">
          <Users className="w-4 h-4 text-purple-400" />

          <h4 className="text-xs font-bold text-slate-200 uppercase">
            Passenger Connections
          </h4>
        </div>

        {passengerDependencies.length === 0 ? (
          <p className="text-xs text-slate-500">
            No passenger connections recorded.
          </p>
        ) : (
          <div className="space-y-2">
            {passengerDependencies.map(renderDependency)}
          </div>
        )}

        <p className="text-[11px] text-slate-500 mt-3">
          Passenger counts are not available from the current backend.
        </p>
      </div>

      {/* CREW DEPENDENCIES */}

      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center gap-2 mb-3">
          <UserCheck className="w-4 h-4 text-cyan-400" />

          <h4 className="text-xs font-bold text-slate-200 uppercase">
            Crew Dependencies
          </h4>
        </div>

        {crewDependencies.length === 0 ? (
          <p className="text-xs text-slate-500">
            No crew dependencies recorded.
          </p>
        ) : (
          <div className="space-y-2">
            {crewDependencies.map(renderDependency)}
          </div>
        )}
      </div>

      {/* GATE DEPENDENCIES */}

      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="w-4 h-4 text-amber-400" />

          <h4 className="text-xs font-bold text-slate-200 uppercase">
            Gate Dependencies
          </h4>
        </div>

        {gateDependencies.length === 0 ? (
          <p className="text-xs text-slate-500">
            No gate dependencies recorded.
          </p>
        ) : (
          <div className="space-y-2">
            {gateDependencies.map(renderDependency)}
          </div>
        )}
      </div>

    </div>
  );
};

export default FlightDependency;