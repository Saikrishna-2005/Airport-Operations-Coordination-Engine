import { useEffect, useState } from "react";
import {
  UserCheck,
  Search,
  AlertTriangle,
  CheckCircle,
  MapPin,
} from "lucide-react";

import api from "../api";

const inputStyle =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white outline-none focus:border-sky-500";

export default function StaffAvailabilityChecker() {
  // ============================================================
  // FORM STATE
  // ============================================================

  const [form, setForm] = useState({
    airport_code: "",
    staff_id: "",
    requested_date: "",
    start_time: "",
    end_time: "",
  });

  // Airport search
  const [airportSearch, setAirportSearch] = useState("");
  const [airports, setAirports] = useState([]);
  const [airportLoading, setAirportLoading] = useState(false);
  const [airportError, setAirportError] = useState("");

  // Airport-specific staff
  const [availableStaff, setAvailableStaff] = useState([]);
  const [staffLoading, setStaffLoading] = useState(false);
  const [staffError, setStaffError] = useState("");

  // Availability results
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ============================================================
  // SEARCH AIRPORTS
  // ============================================================

  useEffect(() => {
    const query = airportSearch.trim();

    if (query.length < 2) {
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
          "Unable to search airports. Please check the backend."
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
  }, [airportSearch]);

  // ============================================================
  // LOAD STAFF FOR SELECTED AIRPORT
  // ============================================================

  useEffect(() => {
    if (!form.airport_code) {
      setAvailableStaff([]);
      setStaffError("");
      setStaffLoading(false);
      return;
    }

    const controller = new AbortController();

    async function loadAirportStaff() {
      try {
        setStaffLoading(true);
        setStaffError("");

        const response = await api.get("/staff/members", {
          params: {
            airport_code: form.airport_code,
          },
          signal: controller.signal,
        });

        const data = response.data;

        const staff = Array.isArray(data)
          ? data
          : Array.isArray(data?.staff)
          ? data.staff
          : Array.isArray(data?.members)
          ? data.members
          : [];

        setAvailableStaff(
          staff.filter(
            (person) =>
              person.employment_status === "active"
          )
        );
      } catch (err) {
        if (err.code === "ERR_CANCELED") return;

        setAvailableStaff([]);
        setStaffError(
          "Unable to load staff for the selected airport."
        );
      } finally {
        if (!controller.signal.aborted) {
          setStaffLoading(false);
        }
      }
    }

    loadAirportStaff();

    return () => controller.abort();
  }, [form.airport_code]);

  // ============================================================
  // HANDLE FORM CHANGES
  // ============================================================

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    setResult(null);
    setError("");
  }

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

    // Backend availability validation currently requires
    // a three-letter airport code.
    if (!/^[A-Z]{3}$/.test(code)) {
      setAirportError(
        "Please select an airport with a valid 3-letter IATA code."
      );
      return;
    }

    setForm((previous) => ({
      ...previous,
      airport_code: code,
      staff_id: "",
    }));

    setAirportSearch("");
    setAirports([]);
    setAirportError("");
    setAvailableStaff([]);
    setResult(null);
    setError("");
  }

  // ============================================================
  // CLEAR AIRPORT
  // ============================================================

  function handleClearAirport() {
    setForm((previous) => ({
      ...previous,
      airport_code: "",
      staff_id: "",
    }));

    setAirportSearch("");
    setAirports([]);
    setAvailableStaff([]);
    setAirportError("");
    setStaffError("");
    setResult(null);
    setError("");
  }

  // ============================================================
  // CHECK STAFF AVAILABILITY
  // ============================================================

  async function handleCheckAvailability(event) {
    event.preventDefault();

    setResult(null);
    setError("");

    if (!form.airport_code) {
      setError("Please select an airport.");
      return;
    }

    if (!form.staff_id.trim()) {
      setError("Please select a staff member.");
      return;
    }

    if (!form.requested_date) {
      setError("Please select a requested date.");
      return;
    }

    if (!form.start_time || !form.end_time) {
      setError("Please select start and end times.");
      return;
    }

    if (form.start_time === form.end_time) {
      setError("Start time and end time cannot be the same.");
      return;
    }

    const requestData = {
      staff_id: form.staff_id.trim(),
      airport_code: form.airport_code,
      requested_date: form.requested_date,
      start_time: form.start_time,
      end_time: form.end_time,
    };

    try {
      setLoading(true);

      const response = await api.post(
        "/staff/availability",
        requestData
      );

      setResult(response.data);
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      if (status === 401) {
        setError(
          "Your session has expired. Please log in again."
        );
      } else if (status === 403) {
        setError(
          "You do not have permission to check staff availability."
        );
      } else if (status === 422) {
        setError(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? detail
                .map((item) => item.msg || "Invalid input")
                .join("; ")
            : "Invalid staff information. Please check your inputs."
        );
      } else {
        setError(
          "Unable to check staff availability. Please verify the backend connection."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  // ============================================================
  // MAIN UI
  // ============================================================

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      {/* HEADER */}

      <div className="mb-5 flex items-center gap-3">
        <UserCheck size={24} className="text-sky-400" />

        <div>
          <h2 className="text-xl font-bold text-white">
            Staff Availability Checker
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Check airport-specific staff availability against
            live SQLite shift and assignment records.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleCheckAvailability}
        className="grid grid-cols-1 gap-4 md:grid-cols-2"
      >
        {/* AIRPORT SELECTION */}

        <div className="space-y-3 md:col-span-2">
          <label className="block space-y-2 text-sm text-slate-300">
            <span className="flex items-center gap-2">
              <MapPin size={16} className="text-sky-400" />
              Airport (Required)
            </span>

            <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3">
              <Search size={18} className="text-slate-400" />

              <input
                type="text"
                value={airportSearch}
                onChange={(event) => {
                  setAirportSearch(event.target.value);

                  if (form.airport_code) {
                    setForm((previous) => ({
                      ...previous,
                      airport_code: "",
                      staff_id: "",
                    }));

                    setAvailableStaff([]);
                  }

                  setResult(null);
                  setError("");
                }}
                placeholder="Search airport by name, city, or IATA code"
                className="w-full bg-transparent py-3 text-sm text-white outline-none"
              />
            </div>
          </label>

          {form.airport_code && (
            <div className="flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
              <p className="text-sm text-emerald-300">
                Selected Airport:{" "}
                <strong>{form.airport_code}</strong>
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

          {airportLoading && (
            <p className="text-sm text-sky-400">
              Searching airports...
            </p>
          )}

          {airportError && (
            <p className="text-sm text-red-400">
              {airportError}
            </p>
          )}

          {airports.length > 0 && (
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

        {/* STAFF SELECTION */}

        <label className="space-y-2 text-sm text-slate-300">
          <span>Staff Member (Required)</span>

          <select
            name="staff_id"
            value={form.staff_id}
            onChange={handleChange}
            disabled={
              !form.airport_code ||
              staffLoading ||
              Boolean(staffError)
            }
            required
            className={inputStyle}
          >
            <option value="">
              {!form.airport_code
                ? "Select an airport first"
                : staffLoading
                ? "Loading airport staff..."
                : "Select a staff member"}
            </option>

            {availableStaff.map((person) => (
              <option
                key={person.staff_id}
                value={person.staff_id}
              >
                {person.full_name} ({person.staff_id}) —{" "}
                {person.role}
              </option>
            ))}
          </select>

          {staffError && (
            <span className="block text-xs text-red-400">
              {staffError}
            </span>
          )}

          {form.airport_code &&
            !staffLoading &&
            !staffError &&
            availableStaff.length === 0 && (
              <span className="block text-xs text-amber-400">
                No active staff members found for this airport.
              </span>
            )}
        </label>

        {/* REQUESTED DATE */}

        <label className="space-y-2 text-sm text-slate-300">
          <span>Requested Date</span>

          <input
            type="date"
            name="requested_date"
            value={form.requested_date}
            onChange={handleChange}
            required
            className={inputStyle}
          />
        </label>

        {/* START TIME */}

        <label className="space-y-2 text-sm text-slate-300">
          <span>Start Time</span>

          <input
            type="time"
            name="start_time"
            value={form.start_time}
            onChange={handleChange}
            required
            className={inputStyle}
          />
        </label>

        {/* END TIME */}

        <label className="space-y-2 text-sm text-slate-300">
          <span>End Time</span>

          <input
            type="time"
            name="end_time"
            value={form.end_time}
            onChange={handleChange}
            required
            className={inputStyle}
          />
        </label>

        {/* SUBMIT BUTTON */}

        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={
              loading ||
              staffLoading ||
              !form.airport_code ||
              !form.staff_id
            }
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-3 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Search size={18} />

            {loading
              ? "Checking..."
              : "Check Staff Availability"}
          </button>
        </div>
      </form>

      <p className="mt-4 text-xs text-amber-400">
        Live database check. Only staff actively assigned to
        the selected airport can be checked. Overnight requests
        are supported.
      </p>

      {/* ERROR MESSAGE */}

      {error && (
        <div
          role="alert"
          className="mt-5 flex items-start gap-3 rounded-lg border border-red-700 bg-red-950 p-4 text-red-300"
        >
          <AlertTriangle size={20} className="shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* AVAILABILITY RESULT */}

      {result && (
        <div className="mt-5 rounded-xl border border-slate-700 bg-slate-950 p-5">
          <h3 className="mb-4 text-lg font-semibold text-white">
            Staff Availability Result
          </h3>

          <p className="mb-2 text-sm text-slate-300">
            <strong>Airport:</strong>{" "}
            {result.airport_code || form.airport_code}
          </p>

          <p className="mb-4 text-sm text-slate-300">
            <strong>Staff ID:</strong> {result.staff_id}
          </p>

          {result.available ? (
            <div className="flex items-start gap-3 rounded-lg border border-emerald-700 bg-emerald-950 p-4 text-emerald-300">
              <CheckCircle
                size={22}
                className="shrink-0"
              />

              <div>
                <p className="font-semibold">
                  Staff Member Available
                </p>

                <p className="mt-1 text-sm">
                  No scheduling conflict was found for the
                  requested interval.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3 rounded-lg border border-amber-700 bg-amber-950 p-4 text-amber-300">
              <AlertTriangle
                size={22}
                className="shrink-0"
              />

              <div>
                <p className="font-semibold">
                  Staff Member Unavailable
                </p>

                <p className="mt-1 text-sm">
                  {result.reason ||
                    "The staff member is unavailable for the requested interval."}
                </p>

                {result.conflicting_assignment && (
                  <div className="mt-3 space-y-1 text-xs">
                    <p>
                      <strong>Conflicting Task:</strong>{" "}
                      {result.conflicting_assignment.task_name}
                    </p>

                    <p>
                      <strong>Gate:</strong>{" "}
                      {result.conflicting_assignment.gate_id ||
                        "Not specified"}
                    </p>

                    <p>
                      <strong>Assignment Date:</strong>{" "}
                      {result.conflicting_assignment.assignment_date}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          <p className="mt-4 text-xs text-slate-400">
            Advisory result only. This check does not create
            or modify staff assignments.
          </p>
        </div>
      )}
    </section>
  );
}