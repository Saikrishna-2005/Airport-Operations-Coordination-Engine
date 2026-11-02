import { useEffect, useState } from "react";
import {
  UserPlus,
  CheckCircle,
  AlertTriangle,
  Search,
  MapPin,
} from "lucide-react";

import api from "../api";

const inputStyle =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white outline-none focus:border-sky-500";

const EMPTY_FORM = {
  airport_code: "",
  staff_id: "",
  assignment_date: "",
  start_time: "",
  end_time: "",
  task_name: "",
  gate_id: "",
};

export default function StaffAllocationForm() {
  const [form, setForm] = useState({ ...EMPTY_FORM });

  const [airportSearch, setAirportSearch] = useState("");
  const [airports, setAirports] = useState([]);
  const [airportLoading, setAirportLoading] = useState(false);
  const [airportError, setAirportError] = useState("");

  const [availableStaff, setAvailableStaff] = useState([]);
  const [staffLoading, setStaffLoading] = useState(false);
  const [staffError, setStaffError] = useState("");

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
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

        // Supports a list or an object containing airport results.
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
          "Unable to search airports. Check the airport search API."
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

        const staff = Array.isArray(response.data?.staff)
          ? response.data.staff
          : [];

        setAvailableStaff(
          staff.filter(
            (person) => person.employment_status === "active"
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
      airport.icao_code ||
      airport.airport_code ||
      airport.code ||
      ""
    )
      .trim()
      .toUpperCase();

    if (!code) {
      setAirportError(
        "Selected airport does not have a valid airport code."
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
    setResult(null);
    setError("");
  }

  // ============================================================
  // ALLOCATE STAFF
  // ============================================================

  async function handleAllocate(event) {
    event.preventDefault();

    setError("");
    setResult(null);

    if (!form.airport_code) {
      setError("Please select an airport.");
      return;
    }

    if (!form.staff_id.trim()) {
      setError("Please select a staff member.");
      return;
    }

    if (!form.task_name.trim()) {
      setError("Please enter a task name.");
      return;
    }

    if (!form.assignment_date) {
      setError("Please select an assignment date.");
      return;
    }

    if (!form.start_time || !form.end_time) {
      setError("Please select the assignment start and end times.");
      return;
    }

    if (form.end_time <= form.start_time) {
      setError(
        "Staff allocation currently supports same-day intervals only."
      );
      return;
    }

    const requestData = {
      airport_code: form.airport_code,
      staff_id: form.staff_id.trim(),
      assignment_date: form.assignment_date,
      start_time: form.start_time,
      end_time: form.end_time,
      task_name: form.task_name.trim(),
      gate_id: form.gate_id.trim() || null,
    };

    try {
      setLoading(true);

      const response = await api.post(
        "/staff/allocate",
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
          "You do not have permission to allocate staff."
        );
      } else if (status === 409) {
        setError(
          typeof detail === "string"
            ? detail
            : "Staff allocation rejected due to a scheduling conflict."
        );
      } else if (status === 422) {
        setError(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? detail
                .map((item) => item.msg || "Invalid input")
                .join("; ")
            : "Invalid allocation details. Please check your inputs."
        );
      } else {
        setError(
          "Unable to allocate staff. Please verify the backend connection."
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
      <div className="mb-5 flex items-center gap-3">
        <UserPlus size={24} className="text-sky-400" />

        <div>
          <h2 className="text-xl font-bold text-white">
            Staff Allocation
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Assign available staff members to airport operational
            tasks using live SQLite records.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleAllocate}
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
                  }

                  setResult(null);
                  setError("");
                }}
                placeholder="Search airport by name, city, IATA or ICAO code"
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
                  airport.icao_code ||
                  airport.airport_code ||
                  airport.code ||
                  "";

                const name =
                  airport.name ||
                  airport.airport_name ||
                  "Unknown Airport";

                return (
                  <button
                    key={`${code}-${index}`}
                    type="button"
                    onClick={() => handleSelectAirport(airport)}
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
                {person.full_name} ({person.staff_id}) — {person.role}
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

        {/* ASSIGNMENT DATE */}

        <label className="space-y-2 text-sm text-slate-300">
          <span>Assignment Date</span>

          <input
            type="date"
            name="assignment_date"
            value={form.assignment_date}
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

        {/* TASK NAME */}

        <label className="space-y-2 text-sm text-slate-300">
          <span>Task Name</span>

          <input
            type="text"
            name="task_name"
            value={form.task_name}
            onChange={handleChange}
            placeholder="e.g. Aircraft Ground Handling"
            maxLength={200}
            required
            className={inputStyle}
          />
        </label>

        {/* GATE ID */}

        <label className="space-y-2 text-sm text-slate-300">
          <span>Gate ID (Optional)</span>

          <input
            type="text"
            name="gate_id"
            value={form.gate_id}
            onChange={handleChange}
            placeholder="e.g. G1"
            maxLength={50}
            className={inputStyle}
          />
        </label>

        {/* SUBMIT BUTTON */}

        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={
              loading ||
              !form.airport_code ||
              !form.staff_id ||
              staffLoading
            }
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-3 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <UserPlus size={18} />

            {loading ? "Allocating..." : "Allocate Staff"}
          </button>
        </div>
      </form>

      <p className="mt-4 text-xs text-amber-400">
        Live database operation. Staff can only be allocated to
        their assigned airport. Successful allocation creates
        a staff assignment in SQLite. Overnight allocation
        is not supported yet.
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

      {/* SUCCESS MESSAGE */}

      {result?.success && (
        <div className="mt-5 rounded-xl border border-emerald-700 bg-emerald-950 p-5">
          <div className="flex items-start gap-3 text-emerald-300">
            <CheckCircle size={24} className="shrink-0" />

            <div>
              <h3 className="font-semibold">
                Staff Allocated Successfully
              </h3>

              <p className="mt-2 text-sm">
                Assignment ID: {result.assignment_id}
              </p>

              <p className="text-sm">
                Airport: {result.airport_code}
              </p>

              <p className="text-sm">
                Staff ID: {result.staff_id}
              </p>

              <p className="text-sm">
                Task: {result.task_name}
              </p>

              <p className="text-sm">
                Date: {result.assignment_date}
              </p>

              <p className="text-sm">
                Time: {result.start_time} – {result.end_time}
              </p>

              <p className="text-sm">
                Gate: {result.gate_id || "Not specified"}
              </p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}