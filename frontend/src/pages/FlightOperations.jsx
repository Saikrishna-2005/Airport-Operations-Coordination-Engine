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
  Plane,
} from "lucide-react";

import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMap } from "react-leaflet";

const toCoordinate = (item) => {
  const rawLat = item?.latitude ?? item?.lat;
  const rawLon = item?.longitude ?? item?.lon ?? item?.lng;
  if (rawLat === null || rawLat === undefined || rawLat === "" || rawLon === null || rawLon === undefined || rawLon === "") return null;
  const lat = Number(rawLat), lon = Number(rawLon);
  return Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? [lat, lon] : null;
};

function FitMapBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 7);
    else if (points.length > 1) map.fitBounds(points, { padding: [28, 28], maxZoom: 9 });
  }, [map, points]);
  return null;
}

function formatWaypointTime(point) {
  const raw = point?.time ?? point?.timestamp ?? point?.last_seen ?? point?.first_seen;
  if (raw === null || raw === undefined) return "Time unavailable";
  const date = typeof raw === "number" ? new Date(raw < 1e12 ? raw * 1000 : raw) : new Date(raw);
  return Number.isNaN(date.getTime()) ? "Time unavailable" : date.toLocaleString();
}

function AircraftMap({ aircraft = [], path = [], title = "Aircraft map" }) {
  const livePoints = aircraft.map((item) => ({ item, position: toCoordinate(item) })).filter((x) => x.position);
  const validWaypoints = path.map((item) => ({ item, position: toCoordinate(item) })).filter((x) => x.position);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  useEffect(() => { setIsPlaying(false); setPlaybackIndex(0); }, [path]);
  useEffect(() => {
    if (!isPlaying || validWaypoints.length < 2) return undefined;
    const timer = window.setInterval(() => {
      setPlaybackIndex((current) => {
        if (current >= validWaypoints.length - 1) { setIsPlaying(false); return current; }
        return current + 1;
      });
    }, Math.max(120, 850 / playbackSpeed));
    return () => window.clearInterval(timer);
  }, [isPlaying, playbackSpeed, validWaypoints.length]);

  const routePoints = validWaypoints.map((x) => x.position);
  const travelledPoints = routePoints.slice(0, playbackIndex + 1);
  const allPoints = [...livePoints.map((x) => x.position), ...routePoints];
  const center = allPoints[0] || [28.5562, 77.1];
  const activeWaypoint = validWaypoints[playbackIndex];
  const canAnimate = validWaypoints.length > 1;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-700">
      <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-950 px-3 py-2 text-xs">
        <span className="font-semibold text-white">{title}</span>
        <span className="text-slate-400">{livePoints.length} aircraft positions · {routePoints.length} trajectory points</span>
      </div>
      <MapContainer center={center} zoom={6} scrollWheelZoom className="h-[420px] w-full" style={{ background: "#0f172a" }}>
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <FitMapBounds points={allPoints} />
        {livePoints.map(({ item, position }, index) => (
          <CircleMarker key={item.icao24 || index} center={position} radius={6} pathOptions={{ color: "#67e8f9", fillColor: "#0891b2", fillOpacity: 0.85 }}>
            <Popup><strong>{String(item.callsign || "Unknown").trim()}</strong><br />ICAO24: {item.icao24 || "—"}<br />Altitude: {item.baro_altitude ?? item.altitude ?? "—"} m<br />Speed: {item.velocity ?? "—"} m/s<br />Heading: {item.true_track ?? item.heading ?? "—"}°</Popup>
          </CircleMarker>
        ))}
        {routePoints.length > 1 && <Polyline positions={routePoints} pathOptions={{ color: "#64748b", weight: 3, opacity: 0.65, dashArray: "6 7" }} />}
        {travelledPoints.length > 1 && <Polyline positions={travelledPoints} pathOptions={{ color: "#a78bfa", weight: 5, opacity: 0.95 }} />}
        {routePoints.length > 0 && <>
          <CircleMarker center={routePoints[0]} radius={7} pathOptions={{ color: "#34d399", fillColor: "#059669", fillOpacity: 1 }}><Popup>Trajectory start</Popup></CircleMarker>
          <CircleMarker center={routePoints[routePoints.length - 1]} radius={7} pathOptions={{ color: "#fbbf24", fillColor: "#d97706", fillOpacity: 1 }}><Popup>Trajectory end</Popup></CircleMarker>
        </>}
        {canAnimate && activeWaypoint && <CircleMarker center={activeWaypoint.position} radius={10} pathOptions={{ color: "#ffffff", weight: 3, fillColor: "#7c3aed", fillOpacity: 1 }}>
          <Popup><strong>Playback aircraft</strong><br />Waypoint: {playbackIndex + 1} / {validWaypoints.length}<br />{formatWaypointTime(activeWaypoint.item)}</Popup>
        </CircleMarker>}
      </MapContainer>
      {canAnimate ? <div className="space-y-3 border-t border-slate-800 bg-slate-950 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => { if (playbackIndex >= validWaypoints.length - 1) setPlaybackIndex(0); setIsPlaying((v) => !v); }} className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white hover:bg-violet-500">{isPlaying ? "Pause" : playbackIndex >= validWaypoints.length - 1 ? "Replay" : "Play"}</button>
          <button type="button" onClick={() => { setIsPlaying(false); setPlaybackIndex(0); }} className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-200 hover:bg-slate-800">Restart</button>
          <label className="flex items-center gap-2 text-xs text-slate-400">Speed
            <select value={playbackSpeed} onChange={(e) => setPlaybackSpeed(Number(e.target.value))} className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-white"><option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option></select>
          </label>
          <span className="ml-auto text-xs text-slate-400">Waypoint {playbackIndex + 1} of {validWaypoints.length}</span>
        </div>
        <input aria-label="Trajectory playback position" type="range" min="0" max={validWaypoints.length - 1} value={playbackIndex} onChange={(e) => { setIsPlaying(false); setPlaybackIndex(Number(e.target.value)); }} className="w-full accent-violet-500" />
        <div className="flex flex-wrap justify-between gap-2 text-[11px] text-slate-400"><span>{formatWaypointTime(validWaypoints[0].item)}</span><span>Current: {activeWaypoint ? formatWaypointTime(activeWaypoint.item) : "—"}</span><span>{formatWaypointTime(validWaypoints[validWaypoints.length - 1].item)}</span></div>
      </div> : <div className="bg-slate-950 px-3 py-2 text-[11px] text-slate-500">{routePoints.length === 1 ? "Only one valid trajectory waypoint was returned; playback needs at least two." : "Load a historical trajectory with at least two valid latitude/longitude waypoints to enable playback."}</div>}
      <p className="bg-slate-950 px-3 py-2 text-[11px] text-slate-500">Playback follows the returned waypoint sequence; it visualizes recorded points and does not predict the aircraft's current position.</p>
    </div>
  );
}


const getHistoricalRows = (payload) => {
  if (!payload || typeof payload !== "object") return [];
  const preferredKeys = ["flights", "arrivals", "departures", "records", "results", "aircraft_history", "data"];
  for (const key of preferredKeys) {
    const value = payload[key];
    if (Array.isArray(value) && value.length && value.some((item) => item && typeof item === "object" && !Array.isArray(item))) return value;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const nested = getHistoricalRows(value);
      if (nested.length) return nested;
    }
  }
  // Handle APIs that return a bare list inside a less common envelope.
  for (const [key, value] of Object.entries(payload)) {
    if (key === "path" || key === "waypoints") continue;
    if (Array.isArray(value) && value.length && value.some((item) => item && typeof item === "object" && !Array.isArray(item))) return value;
  }
  return [];
};

const firstValue = (row, keys) => {
  for (const key of keys) {
    const value = row?.[key];
    if (value !== null && value !== undefined && value !== "") return value;
  }
  return "—";
};

const formatHistoricalTime = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  const date = typeof value === "number" ? new Date(value < 1e12 ? value * 1000 : value) : new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
};

const csvCell = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;

// Flight Operations Components
import { OperationalPulse } from "../components/flight-operations/OperationalPulse";
import { SearchFilter } from "../components/flight-operations/SearchFilter";
import { FlightPriorityBoard } from "../components/flight-operations/FlightPriorityBoard";
import { FlightRiskPanel } from "../components/flight-operations/FlightRiskPanel";

// Flight Operations API Service
import {
  getAllFlights,
  getOperationalPulse,
  getLiveAircraft,
  getHistoricalArrivals,
  getHistoricalDepartures,
  getAircraftHistory,
  getHistoricalInterval,
  getAircraftTrack,
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

  // Live aircraft telemetry is kept separate from operational SQLite flights.
  const [liveAircraftData, setLiveAircraftData] = useState(null);
  const [liveAircraftError, setLiveAircraftError] = useState(null);
  const [liveConnectionStatus, setLiveConnectionStatus] = useState("connecting");
  const [lastLiveSuccessAt, setLastLiveSuccessAt] = useState(null);
  const [selectedAirport, setSelectedAirport] = useState("DEL");
  const [airportInput, setAirportInput] = useState("DEL");

  // Historical OpenSky intelligence (kept separate from operational flights).
  const [historyTab, setHistoryTab] = useState("arrivals");
  const [historyBegin, setHistoryBegin] = useState(() => {
    const d = new Date(Date.now() - 24 * 60 * 60 * 1000);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  });
  const [historyEnd, setHistoryEnd] = useState(() => {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  });
  const [historyIcao24, setHistoryIcao24] = useState("");
  const [historyResult, setHistoryResult] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [historyTableSearch, setHistoryTableSearch] = useState("");

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
  const inFlightRef = useRef(false);
  const pendingRefreshRef = useRef(false);

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
    // Prevent timer/manual/retry triggers from starting overlapping refreshes.
    if (inFlightRef.current) {
      pendingRefreshRef.current = true;
      return;
    }
    inFlightRef.current = true;

    const requestId = ++requestIdRef.current;
    setLiveConnectionStatus("refreshing");

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

      // Fetch live aircraft independently: an OpenSky issue must not break
      // the existing operational flight board.
      try {
        const liveData = await getLiveAircraft({
          airport: selectedAirport,
          radiusDeg: 0.5,
        });

        if (
          mountedRef.current &&
          requestId === requestIdRef.current
        ) {
          setLiveAircraftData(liveData);
          setLiveAircraftError(null);
          setLiveConnectionStatus("connected");
          setLastLiveSuccessAt(new Date());
        }
      } catch (liveErr) {
        console.error("[Flight Operations] Live aircraft request failed:", liveErr);
        if (
          mountedRef.current &&
          requestId === requestIdRef.current
        ) {
          setLiveAircraftError(
            "Live aircraft data is currently unavailable for this airport."
          );
          setLiveConnectionStatus("disconnected");
        }
      }
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
      setLiveConnectionStatus("disconnected");
    } finally {
      inFlightRef.current = false;
      if (pendingRefreshRef.current && mountedRef.current) {
        pendingRefreshRef.current = false;
        window.setTimeout(() => loadData(true), 0);
      }
      if (
        mountedRef.current &&
        requestId === requestIdRef.current
      ) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [selectedAirport]);

  // ============================================================
  // 6. INITIAL DATA LOADING
  // ============================================================

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Refresh both operational data and live aircraft telemetry every 60 seconds.
  useEffect(() => {
    const intervalId = setInterval(() => {
      loadData(true);
    }, 60_000);

    return () => clearInterval(intervalId);
  }, [loadData]);

  // Retry a failed connection after 15 seconds; the request lock prevents overlap.
  useEffect(() => {
    if (liveConnectionStatus !== "disconnected") return undefined;
    const retryId = window.setTimeout(() => loadData(true), 15_000);
    return () => window.clearTimeout(retryId);
  }, [liveConnectionStatus, loadData]);

  const handleAirportSearch = (event) => {
    event.preventDefault();
    const code = airportInput.trim().toUpperCase();
    if (!code) return;
    setSelectedAirport(code);
  };

  const runHistoricalSearch = async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    setHistoryResult(null);
    try {
      const begin = Math.floor(new Date(historyBegin).getTime() / 1000);
      const end = Math.floor(new Date(historyEnd).getTime() / 1000);
      if (!Number.isFinite(begin) || !Number.isFinite(end) || end <= begin) {
        throw new Error("Choose a valid start and end time.");
      }
      let result;
      if (historyTab === "arrivals") {
        result = await getHistoricalArrivals({ airport: selectedAirport, begin, end });
      } else if (historyTab === "departures") {
        result = await getHistoricalDepartures({ airport: selectedAirport, begin, end });
      } else if (historyTab === "aircraft") {
        result = await getAircraftHistory({ icao24: historyIcao24, begin, end });
      } else if (historyTab === "interval") {
        result = await getHistoricalInterval({ begin, end });
      } else {
        const address = historyIcao24.trim().toLowerCase();
        // The tested backend track route accepts a Unix timestamp in `time`.
        result = await getAircraftTrack({ icao24: address, time: end });
      }
      setHistoryResult(result);
    } catch (err) {
      setHistoryError(err?.response?.data?.detail || err.message || "Historical request failed.");
    } finally {
      setHistoryLoading(false);
    }
  };

  const historicalRows = useMemo(() => getHistoricalRows(historyResult), [historyResult]);
  const filteredHistoricalRows = useMemo(() => {
    const term = historyTableSearch.trim().toLowerCase();
    if (!term) return historicalRows;
    return historicalRows.filter((row) => JSON.stringify(row).toLowerCase().includes(term));
  }, [historicalRows, historyTableSearch]);

  const historicalStats = useMemo(() => {
    const uniqueAircraft = new Set(historicalRows.map((row) => String(firstValue(row, ["icao24", "icao_24", "icao"]))).filter((v) => v !== "—"));
    const origins = new Set(historicalRows.map((row) => String(firstValue(row, ["est_departure_airport", "departure_airport", "origin", "origin_airport", "from"]))).filter((v) => v !== "—" && v !== "null"));
    const destinations = new Set(historicalRows.map((row) => String(firstValue(row, ["est_arrival_airport", "arrival_airport", "destination", "destination_airport", "to"]))).filter((v) => v !== "—" && v !== "null"));
    return { total: historicalRows.length || Number(historyResult?.count) || 0, aircraft: uniqueAircraft.size, origins: origins.size, destinations: destinations.size };
  }, [historicalRows, historyResult]);

  const exportHistoricalCsv = () => {
    if (!filteredHistoricalRows.length) return;
    const columns = [
      ["Callsign", ["callsign", "flight", "flight_number"]],
      ["ICAO24", ["icao24", "icao_24"]],
      ["Origin", ["est_departure_airport", "departure_airport", "origin", "origin_airport"]],
      ["Destination", ["est_arrival_airport", "arrival_airport", "destination", "destination_airport"]],
      ["First seen", ["first_seen", "firstSeen", "start_time"]],
      ["Last seen", ["last_seen", "lastSeen", "end_time"]],
    ];
    const lines = [columns.map(([label]) => csvCell(label)).join(",")];
    filteredHistoricalRows.forEach((row) => lines.push(columns.map(([, keys]) => csvCell(firstValue(row, keys))).join(",")));
    const blob = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `opensky-${historyTab}-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

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
        {/* LIVE AIRCRAFT MONITOR */}
        {/* ================================================= */}

        <section className="rounded-2xl border border-cyan-900/60 bg-slate-900/70 p-4 lg:p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-2 text-cyan-300">
                <Plane className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Live Aircraft Monitor</h2>
                <p className="text-xs text-slate-400">
                  OpenSky aircraft state vectors near the selected airport
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2" aria-live="polite">
              <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${
                liveConnectionStatus === "connected"
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : liveConnectionStatus === "refreshing" || liveConnectionStatus === "connecting"
                    ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                    : "border-rose-500/30 bg-rose-500/10 text-rose-300"
              }`}>
                <span className={`h-2 w-2 rounded-full ${
                  liveConnectionStatus === "connected" ? "bg-emerald-400"
                    : liveConnectionStatus === "refreshing" || liveConnectionStatus === "connecting" ? "bg-amber-400 animate-pulse"
                      : "bg-rose-400"
                }`} />
                {liveConnectionStatus === "connected" ? "Connected"
                  : liveConnectionStatus === "refreshing" ? "Refreshing"
                    : liveConnectionStatus === "connecting" ? "Connecting" : "Disconnected"}
              </span>
              <span className="text-[11px] text-slate-500">
                Last success: {lastLiveSuccessAt ? lastLiveSuccessAt.toLocaleTimeString() : "Not yet"}
              </span>
            </div>

            <form onSubmit={handleAirportSearch} className="flex items-center gap-2">
              <label htmlFor="live-airport-code" className="sr-only">Airport code</label>
              <input
                id="live-airport-code"
                value={airportInput}
                onChange={(event) => setAirportInput(event.target.value)}
                placeholder="IATA / ICAO code"
                maxLength={8}
                className="w-36 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white uppercase outline-none focus:border-cyan-500"
              />
              <button
                type="submit"
                disabled={!airportInput.trim()}
                className="rounded-lg bg-cyan-600 px-3 py-2 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50"
              >
                Search
              </button>
            </form>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-300">
              Airport: <strong className="text-cyan-300">{liveAircraftData?.airport_code || selectedAirport}</strong>
            </span>
            <span className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-300">
              Aircraft detected: <strong className="text-white">{liveAircraftData?.aircraft_count ?? "—"}</strong>
            </span>
            <span className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-300">
              Provider: <strong className="text-white">{liveAircraftData?.provider || "OpenSky"}</strong>
            </span>
            <span className="text-slate-500">
              {liveAircraftData?.retrieved_at
                ? `Updated ${new Date(liveAircraftData.retrieved_at).toLocaleTimeString()}`
                : "Waiting for live telemetry"}
            </span>
          </div>

          {liveAircraftError && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{liveAircraftError} The operational flight board remains available.</span>
            </div>
          )}

          {Array.isArray(liveAircraftData?.aircraft) && liveAircraftData.aircraft.length > 0 ? (
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="min-w-full divide-y divide-slate-800 text-left text-xs">
                <thead className="bg-slate-950 text-slate-400">
                  <tr>
                    <th className="px-3 py-2.5 font-semibold">Callsign</th>
                    <th className="px-3 py-2.5 font-semibold">ICAO24</th>
                    <th className="px-3 py-2.5 font-semibold">Altitude (m)</th>
                    <th className="px-3 py-2.5 font-semibold">Speed (m/s)</th>
                    <th className="px-3 py-2.5 font-semibold">Heading</th>
                    <th className="px-3 py-2.5 font-semibold">Ground</th>
                    <th className="px-3 py-2.5 font-semibold">Position</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900/60">
                  {liveAircraftData.aircraft.slice(0, 20).map((aircraft, index) => (
                    <tr key={aircraft.icao24 || index} className="text-slate-300 hover:bg-slate-800/60">
                      <td className="whitespace-nowrap px-3 py-2 font-semibold text-white">
                        {aircraft.callsign?.trim() || "Unknown"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 font-mono">
                        {aircraft.icao24 || "—"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2">
                        {Number.isFinite(Number(aircraft.baro_altitude))
                          ? Math.round(Number(aircraft.baro_altitude))
                          : "—"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2">
                        {Number.isFinite(Number(aircraft.velocity))
                          ? Number(aircraft.velocity).toFixed(1)
                          : "—"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2">
                        {Number.isFinite(Number(aircraft.true_track))
                          ? `${Math.round(Number(aircraft.true_track))}°`
                          : "—"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2">
                        {aircraft.on_ground === true ? "Yes" : aircraft.on_ground === false ? "No" : "—"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 font-mono">
                        {Number.isFinite(Number(aircraft.latitude)) &&
                        Number.isFinite(Number(aircraft.longitude))
                          ? `${Number(aircraft.latitude).toFixed(3)}, ${Number(aircraft.longitude).toFixed(3)}`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {liveAircraftData.aircraft.length > 20 && (
                <p className="border-t border-slate-800 px-3 py-2 text-xs text-slate-500">
                  Showing 20 of {liveAircraftData.aircraft.length} detected aircraft.
                </p>
              )}
            </div>
          ) : (
            <p className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-xs text-slate-400">
              {liveAircraftData
                ? "No aircraft were detected in this airport's current search area."
                : "Live aircraft telemetry will appear here when the backend responds."}
            </p>
          )}

          {Array.isArray(liveAircraftData?.aircraft) && liveAircraftData.aircraft.length > 0 && (
            <AircraftMap aircraft={liveAircraftData.aircraft} title={`Live aircraft positions near ${liveAircraftData.airport_code || selectedAirport}`} />
          )}

          <p className="text-[11px] leading-relaxed text-slate-500">
            Coverage-area detections are not confirmed airport arrivals or departures.
            Aircraft availability depends on OpenSky coverage and API limits.
          </p>
        </section>

        {/* ================================================= */}
        {/* HISTORICAL FLIGHT INTELLIGENCE */}
        {/* ================================================= */}
        <section className="rounded-2xl border border-violet-900/60 bg-slate-900/70 p-4 lg:p-5 space-y-4">
          <div>
            <h2 className="text-sm font-bold text-white">Historical Flight Intelligence</h2>
            <p className="mt-1 text-xs text-slate-400">Explore estimated OpenSky historical records and aircraft trajectories.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {[ ["arrivals", "Arrivals"], ["departures", "Departures"], ["aircraft", "Aircraft History"], ["interval", "Time Interval"], ["track", "Trajectory"] ].map(([key, label]) => (
              <button key={key} type="button" onClick={() => { setHistoryTab(key); setHistoryResult(null); setHistoryError(null); }}
                className={`rounded-lg px-3 py-2 text-xs font-semibold border ${historyTab === key ? "bg-violet-600 border-violet-500 text-white" : "bg-slate-950 border-slate-700 text-slate-300 hover:border-violet-500"}`}>
                {label}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <label className="text-xs text-slate-400">Start time<input type="datetime-local" value={historyBegin} onChange={e => setHistoryBegin(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-white" /></label>
            <label className="text-xs text-slate-400">End time<input type="datetime-local" value={historyEnd} onChange={e => setHistoryEnd(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-white" /></label>
            {(historyTab === "aircraft" || historyTab === "track") && <label className="text-xs text-slate-400">Aircraft ICAO24<input value={historyIcao24} onChange={e => setHistoryIcao24(e.target.value)} placeholder="e.g. 800b05" maxLength={6} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2 font-mono text-white" /></label>}
            <div className="flex items-end"><button type="button" onClick={runHistoricalSearch} disabled={historyLoading} className="w-full rounded-lg bg-violet-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-violet-500 disabled:opacity-50">{historyLoading ? "Loading…" : "Search Historical Data"}</button></div>
          </div>
          {historyError && <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">{historyError}</div>}
          {historyResult && <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300">
              <span className="rounded-lg bg-slate-950 px-3 py-2">Status: <strong>{String(historyResult.status || "received")}</strong></span>
              <span className="rounded-lg bg-amber-500/10 px-3 py-2 text-amber-300">Historical data may be estimated</span>
            </div>

            {historyTab !== "track" && historyTab !== "aircraft" && historyTab !== "interval" ? null : null}

            {historyTab !== "track" && historicalRows.length > 0 && <>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {[
                  ["Historical records", historicalStats.total],
                  ["Unique aircraft", historicalStats.aircraft],
                  ["Estimated origins", historicalStats.origins],
                  ["Estimated destinations", historicalStats.destinations],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                    <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
                    <p className="mt-2 text-2xl font-bold text-white">{value.toLocaleString()}</p>
                  </div>
                ))}
              </div>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">{historyTab === "arrivals" ? "Estimated arrivals" : historyTab === "departures" ? "Estimated departures" : "Historical flight records"}</h3>
                  <p className="text-xs text-slate-500">{filteredHistoricalRows.length.toLocaleString()} of {historicalRows.length.toLocaleString()} records</p>
                </div>
                <div className="flex gap-2">
                  <input value={historyTableSearch} onChange={(e) => setHistoryTableSearch(e.target.value)} placeholder="Search callsign, ICAO24, airport…" className="min-w-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-violet-500" />
                  <button type="button" onClick={exportHistoricalCsv} disabled={!filteredHistoricalRows.length} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-600 disabled:opacity-40">Export CSV</button>
                </div>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="min-w-full divide-y divide-slate-800 text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400">
                    <tr>{["Callsign", "ICAO24", "Estimated origin", "Estimated destination", "First seen", "Last seen"].map((label) => <th key={label} className="whitespace-nowrap px-3 py-3 font-semibold">{label}</th>)}</tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 bg-slate-900/50">
                    {filteredHistoricalRows.slice(0, 100).map((row, index) => (
                      <tr key={`${firstValue(row, ["icao24"])}-${firstValue(row, ["first_seen"])}-${index}`} className="text-slate-300 hover:bg-slate-800/60">
                        <td className="whitespace-nowrap px-3 py-2 font-semibold text-white">{String(firstValue(row, ["callsign", "flight", "flight_number"])).trim()}</td>
                        <td className="whitespace-nowrap px-3 py-2 font-mono">{String(firstValue(row, ["icao24", "icao_24"]))}</td>
                        <td className="whitespace-nowrap px-3 py-2">{String(firstValue(row, ["est_departure_airport", "departure_airport", "origin", "origin_airport"]))}</td>
                        <td className="whitespace-nowrap px-3 py-2">{String(firstValue(row, ["est_arrival_airport", "arrival_airport", "destination", "destination_airport"]))}</td>
                        <td className="whitespace-nowrap px-3 py-2">{formatHistoricalTime(firstValue(row, ["first_seen", "firstSeen", "start_time"]))}</td>
                        <td className="whitespace-nowrap px-3 py-2">{formatHistoricalTime(firstValue(row, ["last_seen", "lastSeen", "end_time"]))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredHistoricalRows.length > 100 && <p className="border-t border-slate-800 px-3 py-2 text-xs text-slate-500">Showing first 100 records. Export CSV to download all filtered records.</p>}
                {filteredHistoricalRows.length === 0 && <p className="p-5 text-center text-xs text-slate-400">No records match your search.</p>}
              </div>
            </>}

            {Array.isArray(historyResult.path) && historyResult.path.length > 0 && (
              <AircraftMap path={historyResult.path} title={`Historical trajectory · ${historyResult.callsign || historyIcao24}`} />
            )}
            {historicalRows.length === 0 && !(Array.isArray(historyResult.path) && historyResult.path.length) && (
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">
                No tabular flight records were returned for this query. Check the response details below if you need to inspect the API payload.
              </div>
            )}
            <details className="rounded-xl border border-slate-800 bg-slate-950">
              <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-cyan-300">Developer: view raw API response</summary>
              <pre className="max-h-96 overflow-auto p-3 text-[11px] leading-relaxed text-emerald-200">{JSON.stringify(historyResult, null, 2)}</pre>
            </details>
          </div>}
          <p className="text-[11px] leading-relaxed text-slate-500">Historical OpenSky records are estimates and are not official airline schedules or confirmed airport arrival/departure records. Trajectory queries use the selected end time as the backend time parameter.</p>
        </section>

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