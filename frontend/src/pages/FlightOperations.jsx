import React, {
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
} from "react";

import {
  RefreshCw,
  Compass,
  AlertCircle,
} from "lucide-react";

// Flight Operations Components
import { OperationalPulse } from "../components/flight-operations/OperationalPulse";
import { SearchFilter } from "../components/flight-operations/SearchFilter";
import { FlightPriorityBoard } from "../components/flight-operations/FlightPriorityBoard";
import { FlightRiskPanel } from "../components/flight-operations/FlightRiskPanel";

// Flight Operations API Service
import {
  getAllFlights,
  getOperationalPulse,
  USE_DEMO_DATA,
} from "../services/flightApi";

/**
 * Flight Operations Control Center
 *
 * Features:
 * - Flight monitoring
 * - Operational pulse statistics
 * - Flight priority management
 * - Flight risk assessment
 * - Search and filtering
 * - Flight sorting
 * - Flight selection
 * - Refresh functionality
 * - UTC clock
 * - AI recommendation interface
 * - Flight impact simulation interface
 *
 * Data source:
 * - Demo data during frontend integration
 * - FastAPI endpoints after backend integration
 */

export const FlightOperations = () => {
  // ============================================================
  // 1. FLIGHT OPERATIONS STATE
  // ============================================================

  const [flights, setFlights] = useState([]);

  const [pulseData, setPulseData] = useState(null);

  const [selectedFlight, setSelectedFlight] = useState(null);

  const [isLoading, setIsLoading] = useState(true);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const [error, setError] = useState(null);

  // ============================================================
  // 2. SEARCH AND FILTER STATE
  // ============================================================

  const [searchTerm, setSearchTerm] = useState("");

  const [riskFilter, setRiskFilter] = useState("ALL");

  const [statusFilter, setStatusFilter] = useState("ALL");

  const [sortBy, setSortBy] = useState("risk");

  // ============================================================
  // 3. UTC CLOCK
  // ============================================================

  const [currentTime, setCurrentTime] = useState(() =>
    new Date().toUTCString().slice(17, 25)
  );

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(
        new Date().toUTCString().slice(17, 25)
      );
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // ============================================================
  // 4. REQUEST LIFECYCLE
  // ============================================================

  const mountedRef = useRef(false);
  const requestIdRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      requestIdRef.current += 1;
    };
  }, []);

  // ============================================================
  // 5. FETCH FLIGHT DATA
  // ============================================================

  const loadData = useCallback(async (silent = false) => {
    const requestId = ++requestIdRef.current;

    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    setError(null);

    try {
      const [flightsData, pulse] = await Promise.all([
        getAllFlights(),
        getOperationalPulse(),
      ]);

      // Ignore outdated requests and unmounted components.
      if (
        !mountedRef.current ||
        requestId !== requestIdRef.current
      ) {
        return;
      }

      if (!Array.isArray(flightsData)) {
        throw new Error("Invalid flight data received.");
      }

      setFlights(flightsData);
      setPulseData(pulse);

      // Preserve the selected flight after refreshing.
      setSelectedFlight((previousFlight) => {
        if (previousFlight) {
          const updatedFlight = flightsData.find(
            (flight) =>
              flight.id === previousFlight.id ||
              flight.flightNumber ===
                previousFlight.flightNumber
          );

          if (updatedFlight) {
            return updatedFlight;
          }
        }

        // Select the highest-priority critical flight.
        const criticalFlight = flightsData.find(
          (flight) => Number(flight.riskScore) >= 80
        );

        return criticalFlight || flightsData[0] || null;
      });
    } catch (err) {
      if (
        !mountedRef.current ||
        requestId !== requestIdRef.current
      ) {
        return;
      }

      console.error(
        "Failed to load Flight Operations data:",
        err
      );

      setError(
        "Unable to retrieve flight telemetry. Please check the API connection."
      );
    } finally {
      if (
        mountedRef.current &&
        requestId === requestIdRef.current
      ) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, []);

  // ============================================================
  // 6. INITIAL DATA LOADING
  // ============================================================

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ============================================================
  // 7. SEARCH, FILTER AND SORT FLIGHTS
  // ============================================================

  const filteredFlights = useMemo(() => {
    return flights
      .filter((flight) => {
        // Search by flight number, airline, origin or destination.
        if (searchTerm.trim()) {
          const term = searchTerm.trim().toLowerCase();

          const matchNumber = flight.flightNumber
            ?.toLowerCase()
            .includes(term);

          const matchAirline = flight.airline
            ?.toLowerCase()
            .includes(term);

          const matchOrigin =
            flight.origin?.code
              ?.toLowerCase()
              .includes(term) ||
            flight.origin?.name
              ?.toLowerCase()
              .includes(term);

          const matchDestination =
            flight.destination?.code
              ?.toLowerCase()
              .includes(term) ||
            flight.destination?.name
              ?.toLowerCase()
              .includes(term);

          if (
            !matchNumber &&
            !matchAirline &&
            !matchOrigin &&
            !matchDestination
          ) {
            return false;
          }
        }

        // Filter by risk level.
        const riskScore = Number(flight.riskScore) || 0;

        if (riskFilter !== "ALL") {
          if (
            riskFilter === "CRITICAL" &&
            riskScore < 80
          ) {
            return false;
          }

          if (
            riskFilter === "HIGH" &&
            (riskScore < 60 || riskScore >= 80)
          ) {
            return false;
          }

          if (
            riskFilter === "MEDIUM" &&
            (riskScore < 30 || riskScore >= 60)
          ) {
            return false;
          }

          if (
            riskFilter === "LOW" &&
            riskScore >= 30
          ) {
            return false;
          }
        }

        // Filter by flight status.
        if (
          statusFilter !== "ALL" &&
          flight.status !== statusFilter
        ) {
          return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "risk") {
          return (
            (Number(b.riskScore) || 0) -
            (Number(a.riskScore) || 0)
          );
        }

        if (sortBy === "delay") {
          return (
            (Number(b.delayMinutes) || 0) -
            (Number(a.delayMinutes) || 0)
          );
        }

        if (sortBy === "flightNumber") {
          return String(a.flightNumber || "").localeCompare(
            String(b.flightNumber || "")
          );
        }

        return 0;
      });
  }, [
    flights,
    searchTerm,
    riskFilter,
    statusFilter,
    sortBy,
  ]);

  // ============================================================
  // 8. RESET FILTERS
  // ============================================================

  const handleResetFilters = () => {
    setSearchTerm("");
    setRiskFilter("ALL");
    setStatusFilter("ALL");
    setSortBy("risk");
  };

  // ============================================================
  // 9. REFRESH FLIGHT OPERATIONS
  // ============================================================

  const handleRefresh = () => {
    loadData(true);
  };

  // ============================================================
  // 10. AI DECISION UPDATE CALLBACK
  // ============================================================

  const handleDecisionUpdated = () => {
    // Refresh flight information after a decision action.
    loadData(true);
  };

  // ============================================================
  // 11. FLIGHT OPERATIONS INTERFACE
  // ============================================================

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">

      {/* ===================================================== */}
      {/* FLIGHT OPERATIONS HEADER */}
      {/* ===================================================== */}

      <header className="sticky top-0 z-30 bg-slate-950/90 backdrop-blur-md border-b border-slate-800 px-4 lg:px-8 py-3.5 shadow-md">

        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">

          {/* Header Title */}

          <div className="flex items-center gap-3">

            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Compass className="w-5 h-5 animate-pulse" />
            </div>

            <div>

              <h1 className="text-lg lg:text-xl font-black tracking-tight text-white flex items-center gap-2">

                Flight Operations Control Deck

                <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
                  DISPATCH v2.4
                </span>

              </h1>

              <p className="text-xs text-slate-400">
                AeroPulse Multi-Agent Dispatch & Network Risk
                Mitigation Engine
              </p>

            </div>

          </div>

          {/* UTC CLOCK + MODE + REFRESH */}

          <div className="flex items-center gap-3">

            {/* UTC Clock */}

            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs">

              <span className="text-slate-500 font-semibold">
                UTC:
              </span>

              <span className="text-cyan-400 font-bold">
                {currentTime}
              </span>

            </div>

            {/* Data Source Indicator */}

            <div
              className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${
                USE_DEMO_DATA
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              }`}
            >
              {USE_DEMO_DATA
                ? "MIXED MODE"
                : "MIXED MODE"}
            </div>

            {/* Refresh Button */}

            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing || isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs font-medium text-slate-200 transition-colors shadow-sm disabled:opacity-50"
              title="Refresh flight telemetry"
            >

              <RefreshCw
                className={`w-3.5 h-3.5 text-cyan-400 ${
                  isRefreshing ? "animate-spin" : ""
                }`}
              />

              <span className="hidden sm:inline">
                Refresh
              </span>

            </button>

          </div>

        </div>

      </header>

      {/* ===================================================== */}
      {/* MAIN FLIGHT OPERATIONS CONTENT */}
      {/* ===================================================== */}

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 lg:p-6 space-y-5">

        {/* Error Notification */}

        {error && (

          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between gap-3">

            <div className="flex items-center gap-2">

              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />

              <span>
                {error}
              </span>

            </div>

            <button
              type="button"
              onClick={() => loadData()}
              className="underline hover:text-white"
            >
              Retry
            </button>

          </div>

        )}

        {/* ================================================= */}
        {/* OPERATIONAL PULSE */}
        {/* ================================================= */}

        <OperationalPulse
          pulseData={pulseData}
          isLiveApi={pulseData !== null}
        />

        {/* ================================================= */}
        {/* SEARCH AND FILTER */}
        {/* ================================================= */}

        <SearchFilter
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          riskFilter={riskFilter}
          onRiskFilterChange={setRiskFilter}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          sortBy={sortBy}
          onSortChange={setSortBy}
          onResetFilters={handleResetFilters}
          resultCount={filteredFlights.length}
          totalCount={flights.length}
        />

        {/* ================================================= */}
        {/* FLIGHT PRIORITY BOARD + FLIGHT RISK PANEL */}
        {/* ================================================= */}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">

          {/* LEFT SIDE — FLIGHT PRIORITY BOARD */}

          <div className="lg:col-span-5 h-[800px]">

            <FlightPriorityBoard
              flights={filteredFlights}
              selectedFlightId={
                selectedFlight?.id ||
                selectedFlight?.flightNumber
              }
              onSelectFlight={setSelectedFlight}
              isLoading={isLoading}
            />

          </div>

          {/* RIGHT SIDE — FLIGHT RISK PANEL */}

          <div className="lg:col-span-7 h-[800px]">

            <FlightRiskPanel
              flight={selectedFlight}
              onDecisionUpdated={handleDecisionUpdated}
            />

          </div>

        </div>

      </main>

      {/* ===================================================== */}
      {/* FOOTER */}
      {/* ===================================================== */}

      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 px-6 text-center text-xs text-slate-500">

        <p className="font-mono">
          Flight Operations Control Center &bull;{" "}
          {USE_DEMO_DATA
            ? "Mixed Mode (Live Flights / Demo Pulse)"
            : "Mixed Mode (Live Flights / Demo Pulse)"}
          {" "}&bull; Flight List Connected; Other Modules Pending
        </p>

      </footer>

    </div>
  );
};

export default FlightOperations;