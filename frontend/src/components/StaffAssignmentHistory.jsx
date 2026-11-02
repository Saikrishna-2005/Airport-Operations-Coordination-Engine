import { useEffect, useRef, useState } from "react";
import {
  History,
  Search,
  MapPin,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";

import api from "../api";

const inputStyle =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white outline-none focus:border-sky-500";

export default function StaffAssignmentHistory() {
  // ============================================================
  // STATE
  // ============================================================

  const [airportSearch, setAirportSearch] = useState("");
  const [airports, setAirports] = useState([]);
  const [selectedAirport, setSelectedAirport] = useState("");

  const [airportLoading, setAirportLoading] = useState(false);
  const [airportError, setAirportError] = useState("");

  const [staffId, setStaffId] = useState("");
  const [includeUnknown, setIncludeUnknown] = useState(false);

  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const historyRequestId = useRef(0);

  // ============================================================
  // RESET PREVIOUS RESULTS
  // ============================================================

  function clearResults() {
    historyRequestId.current += 1;
    setAssignments([]);
    setSearched(false);
    setError("");
    setLoading(false);
  }

  // ============================================================
  // SEARCH AIRPORTS
  // ============================================================

  useEffect(() => {
    const query = airportSearch.trim();

    if (query.length < 2 || includeUnknown) {
      setAirports([]);
      setAirportError("");
      setAirportLoading(false);
      return;
    }

    const controller = new AbortController();

    const timer = setTimeout(async () => {
      try {
        setAirportLoading(true);
        setAirportError("");

        const response = await api.get(
          "/weather/airports/search",
          {
            params: {
              q: query,
              limit: 15,
            },
            signal: controller.signal,
          }
        );

        if (controller.signal.aborted) return;

        const data = response.data;

        const results = Array.isArray(data)
          ? data
          : Array.isArray(data?.airports)
          ? data.airports
          : Array.isArray(data?.results)
          ? data.results
          : [];

        setAirports(results);
      } catch (err) {
        if (err.code === "ERR_CANCELED") return;

        setAirports([]);
        setAirportError(
          "Unable to search airports. Check the backend connection."
        );
      } finally {
        if (!controller.signal.aborted) {
          setAirportLoading(false);
        }
      }
    }, 350);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [airportSearch, includeUnknown]);

  // ============================================================
  // SELECT AIRPORT
  // ============================================================

  function handleSelectAirport(airport) {
    const code = String(
      airport.iata_code ||
      airport.airport_code ||
      airport.code ||
      airport.icao_code ||
      ""
    )
      .trim()
      .toUpperCase();

    if (!/^[A-Z]{3,4}$/.test(code)) {
      setAirportError(
        "Please select an airport with a valid IATA or ICAO code."
      );
      return;
    }

    setSelectedAirport(code);
    setAirportSearch("");
    setAirports([]);
    setAirportError("");
    setIncludeUnknown(false);

    clearResults();
  }

  // ============================================================
  // CLEAR AIRPORT
  // ============================================================

  function handleClearAirport() {
    setSelectedAirport("");
    setAirportSearch("");
    setAirports([]);
    setAirportError("");

    clearResults();
  }

  // ============================================================
  // HANDLE UNKNOWN AIRPORT HISTORY
  // ============================================================

  function handleUnknownChange(event) {
    const checked = event.target.checked;

    setIncludeUnknown(checked);
    setSelectedAirport("");
    setAirportSearch("");
    setAirports([]);
    setAirportError("");

    clearResults();
  }

  // ============================================================
  // LOAD ASSIGNMENT HISTORY
  // ============================================================

  async function handleLoadHistory(event) {
    event.preventDefault();

    if (loading) return;

    clearResults();

    if (!selectedAirport && !includeUnknown) {
      setError("Please select an airport.");
      return;
    }

    const requestId = historyRequestId.current;

    const params = {};

    if (includeUnknown) {
      params.include_unknown = true;
    } else {
      params.airport_code = selectedAirport;
    }

    if (staffId.trim()) {
      params.staff_id = staffId.trim();
    }

    try {
      setLoading(true);

      const response = await api.get(
        "/staff/assignments/history",
        { params }
      );

      if (requestId !== historyRequestId.current) return;

      setAssignments(
        Array.isArray(response.data?.assignments)
          ? response.data.assignments
          : []
      );

      setSearched(true);
    } catch (err) {
      if (requestId !== historyRequestId.current) return;

      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      if (status === 401) {
        setError(
          "Your session has expired. Please log in again."
        );
      } else if (status === 403) {
        setError(
          "You do not have permission to view this assignment history."
        );
      } else if (status === 422) {
        setError(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? detail
                .map((item) => item.msg || "Invalid input")
                .join("; ")
            : "Invalid history search parameters."
        );
      } else {
        setError(
          "Unable to load assignment history. Check the backend connection."
        );
      }
    } finally {
      if (requestId === historyRequestId.current) {
        setLoading(false);
      }
    }
  }

  // ============================================================
  // MAIN UI
  // ============================================================

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">

      {/* HEADER */}

      <div className="mb-5 flex items-center gap-3">
        <History size={24} className="text-sky-400" />

        <div>
          <h2 className="text-xl font-bold text-white">
            Staff Assignment History
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            View airport-specific staff assignments stored
            in the SQLite database.
          </p>
        </div>
      </div>

      {/* SEARCH FORM */}

      <form
        onSubmit={handleLoadHistory}
        className="space-y-4"
      >

        {/* AIRPORT SEARCH */}

        <div className="space-y-3">
          <label className="block space-y-2 text-sm text-slate-300">

            <span className="flex items-center gap-2">
              <MapPin size={16} className="text-sky-400" />
              Airport
            </span>

            <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3">

              <Search
                size={18}
                className="text-slate-400"
              />

              <input
                type="text"
                value={airportSearch}
                disabled={includeUnknown}
                onChange={(event) => {
                  setAirportSearch(event.target.value);

                  if (selectedAirport) {
                    setSelectedAirport("");
                  }

                  clearResults();
                }}
                placeholder="Search airport by name, city, IATA or ICAO code"
                className="w-full bg-transparent py-3 text-sm text-white outline-none disabled:opacity-50"
              />

            </div>
          </label>

          {/* SELECTED AIRPORT */}

          {selectedAirport && (
            <div className="flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">

              <p className="text-sm text-emerald-300">
                Selected Airport:{" "}
                <strong>{selectedAirport}</strong>
              </p>

              <button
                type="button"
                onClick={handleClearAirport}
                className="text-xs font-semibold text-emerald-300 hover:text-white"
              >
                Change Airport
              </button>

            </div>
          )}

          {/* AIRPORT LOADING */}

          {airportLoading && (
            <p className="text-sm text-sky-400">
              Searching airports...
            </p>
          )}

          {/* AIRPORT ERROR */}

          {airportError && (
            <p className="text-sm text-red-400">
              {airportError}
            </p>
          )}

          {/* AIRPORT RESULTS */}

          {airports.length > 0 && !includeUnknown && (
            <div className="max-h-56 overflow-y-auto rounded-lg border border-slate-700 bg-slate-950">

              {airports.map((airport, index) => {
                const code =
                  airport.iata_code ||
                  airport.airport_code ||
                  airport.code ||
                  airport.icao_code ||
                  "";

                const name =
                  airport.name ||
                  airport.airport_name ||
                  "Unknown Airport";

                return (
                  <button
                    key={`${code}-${index}`}
                    type="button"
                    onClick={() =>
                      handleSelectAirport(airport)
                    }
                    className="block w-full border-b border-slate-800 px-4 py-3 text-left text-sm text-white hover:bg-slate-800"
                  >
                    <span className="font-semibold">
                      {code}
                    </span>

                    <span className="ml-2 text-slate-400">
                      {name}
                    </span>
                  </button>
                );
              })}

            </div>
          )}
        </div>

        {/* STAFF ID FILTER */}

        <label className="block space-y-2 text-sm text-slate-300">

          <span>Staff ID (Optional)</span>

          <input
            type="text"
            value={staffId}
            onChange={(event) => {
              setStaffId(event.target.value);
              clearResults();
            }}
            placeholder="e.g. HYD_STAFF_001"
            maxLength={50}
            className={inputStyle}
          />

        </label>

        {/* UNKNOWN HISTORICAL RECORDS */}

        <label className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-950 p-3">

          <input
            type="checkbox"
            checked={includeUnknown}
            onChange={handleUnknownChange}
            className="h-4 w-4 accent-sky-500"
          />

          <span className="text-sm text-slate-300">
            View historical assignments with unknown airports

            <span className="ml-2 text-xs text-amber-400">
              (Admin only)
            </span>
          </span>

        </label>

        {/* LOAD BUTTON */}

        <button
          type="submit"
          disabled={
            loading ||
            (!selectedAirport && !includeUnknown)
          }
          className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-3 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            size={18}
            className={loading ? "animate-spin" : ""}
          />

          {loading
            ? "Loading History..."
            : "Load Assignment History"}
        </button>

      </form>

      {/* ERROR MESSAGE */}

      {error && (
        <div
          role="alert"
          className="mt-5 flex items-start gap-3 rounded-lg border border-red-700 bg-red-950 p-4 text-red-300"
        >
          <AlertTriangle
            size={20}
            className="shrink-0"
          />

          <p>{error}</p>
        </div>
      )}

      {/* RESULTS */}

      {searched && !error && (
        <div className="mt-6">

          {/* RESULTS HEADER */}

          <div className="mb-4 flex items-center justify-between">

            <h3 className="text-lg font-semibold text-white">
              Assignment Records
            </h3>

            <span className="rounded-lg bg-slate-800 px-3 py-1 text-sm text-sky-300">
              Total: {assignments.length}
            </span>

          </div>

          {/* EMPTY RESULTS */}

          {assignments.length === 0 ? (
            <div className="rounded-lg border border-slate-700 bg-slate-950 p-5 text-sm text-slate-400">
              No staff assignments found for the selected filters.
            </div>
          ) : (

            /* ASSIGNMENT TABLE */

            <div className="overflow-x-auto rounded-lg border border-slate-700">

              <table className="min-w-full divide-y divide-slate-700 text-left text-sm">

                <thead className="bg-slate-950 text-slate-300">
                  <tr>
                    <th className="px-4 py-3">ID</th>
                    <th className="px-4 py-3">Airport</th>
                    <th className="px-4 py-3">Staff</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Task</th>
                    <th className="px-4 py-3">Gate</th>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Time</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-800 bg-slate-900 text-slate-300">

                  {assignments.map((assignment) => (
                    <tr
                      key={assignment.id}
                      className="hover:bg-slate-800/60"
                    >

                      <td className="px-4 py-3">
                        {assignment.id}
                      </td>

                      <td className="px-4 py-3">
                        {assignment.airport_code || "Unknown"}
                      </td>

                      <td className="px-4 py-3">
                        <div className="font-medium text-white">
                          {assignment.full_name || "Unknown"}
                        </div>

                        <div className="text-xs text-slate-400">
                          {assignment.staff_id}
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        {assignment.role || "N/A"}
                      </td>

                      <td className="px-4 py-3">
                        {assignment.task_name}
                      </td>

                      <td className="px-4 py-3">
                        {assignment.gate_id || "Not specified"}
                      </td>

                      <td className="px-4 py-3">
                        {assignment.assignment_date}
                      </td>

                      <td className="whitespace-nowrap px-4 py-3">
                        {assignment.start_time} –{" "}
                        {assignment.end_time}
                      </td>

                    </tr>
                  ))}

                </tbody>
              </table>

            </div>
          )}
        </div>
      )}

    </section>
  );
}