import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Users,
  UserCheck,
  UserX,
  Search,
  UserPlus,
  Pencil,
  Trash2,
  RefreshCw,
  X,
  Save,
  Clock3,
} from "lucide-react";

import api from "../api";
import StaffAvailabilityChecker from "../components/StaffAvailabilityChecker";
import StaffAllocationForm from "../components/StaffAllocationForm";
import StaffAssignmentHistory from "../components/StaffAssignmentHistory";

// ============================================================
// CONSTANTS
// ============================================================

const STAFF_ROLES = [
  "Ground Staff",
  "Ground Operations",
  "Ramp Agent",
  "Security",
  "Passenger Support",
  "Operations",
  "Maintenance",
  "Other",
];

const EMPLOYMENT_STATUSES = ["active", "inactive"];

const EMPTY_STAFF = {
  staff_id: "",
  full_name: "",
  role: "Ground Operations",
  employment_status: "active",
  airport_code: "",
  shift_date: "",
  shift_start_time: "09:00",
  shift_end_time: "17:00",
};

const inputStyle =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white outline-none focus:border-sky-500";

const buttonStyle =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50";

// ============================================================
// HELPERS
// ============================================================

function getApiError(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || "Invalid input")
      .join("; ");
  }

  return fallback;
}

function minuteToTime(minute) {
  if (minute === null || minute === undefined) {
    return "--:--";
  }

  const normalized = ((Number(minute) % 1440) + 1440) % 1440;

  const hours = Math.floor(normalized / 60);
  const minutes = normalized % 60;

  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function isOvernightShift(shift) {
  return Number(shift.end_minute) > 1440;
}

function validateShiftTimes(startTime, endTime) {
  if (!startTime || !endTime) {
    return "Shift start time and end time are required.";
  }

  if (startTime === endTime) {
    return "Shift start and end times cannot be equal.";
  }

  return "";
}

// ============================================================
// SEARCHABLE AIRPORT PICKER
// ============================================================

function AirportPicker({ value, onChange, label, allowAll = false, disabled = false }) {
  const [query, setQuery] = useState(value || "");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setQuery(value || "");
  }, [value]);

  useEffect(() => {
    const term = query.trim();
    if (!term || (value && term.toUpperCase() === value.toUpperCase())) {
      setResults([]);
      setError("");
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await api.get("/weather/airports/search", {
          params: { q: term, limit: 15 },
        });
        const data = response.data;
        const list = Array.isArray(data) ? data :
          (data?.airports || data?.results || data?.matches || []);
        if (!cancelled) {
          setResults(Array.isArray(list) ? list : []);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setResults([]);
          setError(getApiError(err, "Airport search unavailable."));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query, value]);

  return (
    <div className="relative space-y-2 text-sm text-slate-300">
      <label className="block" htmlFor={`airport-${label.replace(/\W/g, "-")}`}>
        {label}
      </label>
      <input
        id={`airport-${label.replace(/\W/g, "-")}`}
        value={query}
        disabled={disabled}
        autoComplete="off"
        placeholder="Search airport code, name, or city..."
        className={inputStyle}
        onChange={(event) => {
          setQuery(event.target.value);
          onChange(""); // Only a selected catalog result is valid.
        }}
      />
      {allowAll && (
        <button type="button" disabled={disabled} onClick={() => { onChange(""); setQuery(""); setResults([]); }}
          className="text-xs text-sky-400 hover:underline">
          Show All Airports
        </button>
      )}
      {loading && <p className="text-xs text-slate-400">Searching airports...</p>}
      {error && <p className="text-xs text-red-400">{error}</p>}
      {results.length > 0 && (
        <div className="z-30 max-h-52 overflow-y-auto rounded-lg border border-slate-700 bg-slate-800 shadow-xl">
          {results.map((airport, index) => {
            const code = String(airport.airport_code || airport.iata_code || airport.iata || airport.code || "").toUpperCase();
            const name = airport.name || airport.airport_name || airport.city || "Airport";
            if (!/^[A-Z]{3}$/.test(code)) return null;
            return (
              <button type="button" key={`${code}-${index}`} disabled={disabled}
                className="block w-full px-3 py-2 text-left text-sm text-white hover:bg-slate-700"
                onClick={() => { onChange(code); setQuery(code); setResults([]); }}>
                <strong>{code}</strong> — {name}
              </button>
            );
          })}
        </div>
      )}
      {value && <p className="text-xs text-emerald-400">Selected: {value}</p>}
    </div>
  );
}

// ============================================================
// SUMMARY CARD
// ============================================================

function SummaryCard({ title, value, icon: Icon, color }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">{title}</p>
        <Icon size={22} className={color} />
      </div>

      <p className="mt-4 text-3xl font-bold text-white">{value}</p>

      <p className="mt-2 text-xs text-slate-500">
        Live SQLite staff directory
      </p>
    </div>
  );
}

// ============================================================
// STAFF FIELDS
// ============================================================

function StaffFields({
  form,
  setForm,
  includeId = false,
  disabled = false,
}) {
  const roleOptions = STAFF_ROLES.includes(form.role)
    ? STAFF_ROLES
    : [form.role, ...STAFF_ROLES];

  return (
    <>
      {includeId && (
        <label className="space-y-2 text-sm text-slate-300">
          <span>Staff ID</span>

          <input
            required
            maxLength={50}
            disabled={disabled}
            value={form.staff_id}
            onChange={(event) =>
              setForm((previous) => ({
                ...previous,
                staff_id: event.target.value,
              }))
            }
            placeholder="e.g. ST003"
            className={inputStyle}
          />
        </label>
      )}

      <label className="space-y-2 text-sm text-slate-300">
        <span>Full Name</span>

        <input
          required
          maxLength={150}
          disabled={disabled}
          value={form.full_name}
          onChange={(event) =>
            setForm((previous) => ({
              ...previous,
              full_name: event.target.value,
            }))
          }
          placeholder="Enter staff name"
          className={inputStyle}
        />
      </label>

      <label className="space-y-2 text-sm text-slate-300">
        <span>Role</span>

        <select
          required
          disabled={disabled}
          value={form.role}
          onChange={(event) =>
            setForm((previous) => ({
              ...previous,
              role: event.target.value,
            }))
          }
          className={inputStyle}
        >
          {roleOptions.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-2 text-sm text-slate-300">
        <span>Employment Status</span>

        <select
          required
          disabled={disabled}
          value={form.employment_status}
          onChange={(event) =>
            setForm((previous) => ({
              ...previous,
              employment_status: event.target.value,
            }))
          }
          className={inputStyle}
        >
          {EMPLOYMENT_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status === "active" ? "Active" : "Inactive"}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

// ============================================================
// SHIFT FIELDS
// ============================================================

function ShiftFields({ form, setForm, disabled = false }) {
  return (
    <>
      <label className="space-y-2 text-sm text-slate-300">
        <span>Shift Date *</span>

        <input
          type="date"
          required
          disabled={disabled}
          value={form.shift_date}
          onChange={(event) =>
            setForm((previous) => ({
              ...previous,
              shift_date: event.target.value,
            }))
          }
          className={inputStyle}
        />
      </label>

      <label className="space-y-2 text-sm text-slate-300">
        <span>Shift Start Time *</span>

        <input
          type="time"
          required
          disabled={disabled}
          value={form.shift_start_time}
          onChange={(event) =>
            setForm((previous) => ({
              ...previous,
              shift_start_time: event.target.value,
            }))
          }
          className={inputStyle}
        />
      </label>

      <label className="space-y-2 text-sm text-slate-300">
        <span>Shift End Time *</span>

        <input
          type="time"
          required
          disabled={disabled}
          value={form.shift_end_time}
          onChange={(event) =>
            setForm((previous) => ({
              ...previous,
              shift_end_time: event.target.value,
            }))
          }
          className={inputStyle}
        />
      </label>
    </>
  );
}

// ============================================================
// MAIN STAFF COMPONENT
// ============================================================

export default function Staff({ userRole }) {
  const isAdmin = userRole === "admin";

  // ----------------------------------------------------------
  // STAFF STATE
  // ----------------------------------------------------------

  const [databaseStaff, setDatabaseStaff] = useState([]);
  const [staffLoading, setStaffLoading] = useState(true);
  const [staffError, setStaffError] = useState("");

  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selectedAirport, setSelectedAirport] = useState("");

  const [showAddForm, setShowAddForm] = useState(false);
  const [newStaff, setNewStaff] = useState({ ...EMPTY_STAFF });

  const [editingStaff, setEditingStaff] = useState(null);
  const [editForm, setEditForm] = useState(null);

  const [deletingId, setDeletingId] = useState(null);

  // ----------------------------------------------------------
  // SHIFT STATE
  // ----------------------------------------------------------

  const [staffShifts, setStaffShifts] = useState([]);
  const [shiftsLoading, setShiftsLoading] = useState(true);
  const [shiftError, setShiftError] = useState("");

  const [editingShift, setEditingShift] = useState(null);
  const [shiftEditForm, setShiftEditForm] = useState(null);

  const [shiftSearch, setShiftSearch] = useState("");

  // ==========================================================
  // LOAD STAFF
  // ==========================================================

  const loadStaff = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setStaffLoading(true);
    }

    try {
      const response = await api.get("/staff/members", {
        params: selectedAirport ? { airport_code: selectedAirport } : {},
      });

      setDatabaseStaff(
        Array.isArray(response.data?.staff)
          ? response.data.staff
          : []
      );

      setStaffError("");

      return true;
    } catch (error) {
      setStaffError(
        getApiError(
          error,
          "Unable to load staff records from SQLite."
        )
      );

      return false;
    } finally {
      if (showLoading) {
        setStaffLoading(false);
      }
    }
  }, [selectedAirport]);

  // ==========================================================
  // LOAD SHIFTS
  // ==========================================================

  const loadShifts = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setShiftsLoading(true);
    }

    try {
      const response = await api.get("/staff/shifts", {
        params: selectedAirport ? { airport_code: selectedAirport } : {},
      });

      setStaffShifts(
        Array.isArray(response.data?.shifts)
          ? response.data.shifts
          : []
      );

      setShiftError("");

      return true;
    } catch (error) {
      setShiftError(
        getApiError(
          error,
          "Unable to load staff shifts."
        )
      );

      return false;
    } finally {
      if (showLoading) {
        setShiftsLoading(false);
      }
    }
  }, [selectedAirport]);

  // ==========================================================
  // LOAD DATA WHEN THE SELECTED AIRPORT CHANGES
  // ==========================================================

  useEffect(() => {
    loadStaff();
    loadShifts();
  }, [loadStaff, loadShifts]);

  // ==========================================================
  // STAFF STATISTICS
  // ==========================================================

  const statistics = useMemo(
    () => ({
      total: databaseStaff.length,

      active: databaseStaff.filter(
        (person) => person.employment_status === "active"
      ).length,

      inactive: databaseStaff.filter(
        (person) => person.employment_status === "inactive"
      ).length,
    }),
    [databaseStaff]
  );

  // ==========================================================
  // FILTER STAFF
  // ==========================================================

  const filteredStaff = useMemo(() => {
    const query = search.trim().toLowerCase();

    return databaseStaff.filter((person) => {
      const matchesStatus =
        statusFilter === "All" ||
        person.employment_status === statusFilter;

      const matchesSearch = [
        person.staff_id,
        person.full_name,
        person.role,
        person.employment_status,
      ].some((value) =>
        String(value ?? "").toLowerCase().includes(query)
      );

      return matchesStatus && matchesSearch;
    });
  }, [databaseStaff, search, statusFilter]);

  // ==========================================================
  // FILTER SHIFTS
  // ==========================================================

  const filteredShifts = useMemo(() => {
    const query = shiftSearch.trim().toLowerCase();

    return staffShifts.filter((shift) =>
      [
        shift.staff_id,
        shift.full_name,
        shift.role,
        shift.shift_date,
      ].some((value) =>
        String(value ?? "").toLowerCase().includes(query)
      )
    );
  }, [staffShifts, shiftSearch]);

  // ==========================================================
  // ADD STAFF WITH MANDATORY INITIAL SHIFT
  // ==========================================================

  async function handleAddStaff(event) {
    event.preventDefault();

    if (!isAdmin || saving) return;

    setMessage("");
    setStaffError("");

    if (!newStaff.airport_code) {
      setStaffError("Please select an airport from the search results.");
      return;
    }

    if (!newStaff.shift_date) {
      setStaffError("Please select an initial shift date.");
      return;
    }

    const timingError = validateShiftTimes(
      newStaff.shift_start_time,
      newStaff.shift_end_time
    );

    if (timingError) {
      setStaffError(timingError);
      return;
    }

    setSaving(true);

    try {
      const payload = {
        staff_id: newStaff.staff_id.trim(),
        full_name: newStaff.full_name.trim(),
        role: newStaff.role.trim(),
        employment_status: newStaff.employment_status,
        airport_code: newStaff.airport_code,

        // Mandatory initial shift
        shift_date: newStaff.shift_date,
        shift_start_time: newStaff.shift_start_time,
        shift_end_time: newStaff.shift_end_time,
      };

      await api.post("/staff/members", payload);

      setShowAddForm(false);
      setNewStaff({ ...EMPTY_STAFF });

      setMessage(
        `Staff member ${payload.full_name} (${payload.staff_id}) created with an initial shift.`
      );

      await Promise.all([
        loadStaff(false),
        loadShifts(false),
      ]);
    } catch (error) {
      setStaffError(
        getApiError(
          error,
          "Unable to add staff member with initial shift."
        )
      );
    } finally {
      setSaving(false);
    }
  }

  // ==========================================================
  // EDIT STAFF DETAILS
  // ==========================================================

  function handleEditStaff(person) {
    if (!isAdmin) return;

    setEditingStaff(person.staff_id);

    setEditForm({
      full_name: person.full_name,
      role: person.role,
      employment_status: person.employment_status,
    });

    setMessage("");
    setStaffError("");
  }

  // ==========================================================
  // SAVE STAFF DETAILS
  // ==========================================================

  async function handleSaveEdit(event) {
    event.preventDefault();

    if (!isAdmin || !editingStaff || !editForm || saving) {
      return;
    }

    setSaving(true);
    setMessage("");
    setStaffError("");

    try {
      await api.put(
        `/staff/members/${encodeURIComponent(editingStaff)}`,
        {
          full_name: editForm.full_name.trim(),
          role: editForm.role.trim(),
          employment_status: editForm.employment_status,
        }
      );

      const updatedStaffId = editingStaff;

      setEditingStaff(null);
      setEditForm(null);

      setMessage(
        `Staff member ${updatedStaffId} updated successfully.`
      );

      await Promise.all([
        loadStaff(false),
        loadShifts(false),
      ]);
    } catch (error) {
      setStaffError(
        getApiError(
          error,
          "Unable to update staff member."
        )
      );
    } finally {
      setSaving(false);
    }
  }

  // ==========================================================
  // DELETE STAFF
  // ==========================================================

  async function handleDeleteStaff(person) {
    if (!isAdmin || saving) return;

    const confirmed = window.confirm(
      `Delete ${person.full_name} (${person.staff_id})?\n\n` +
      "Staff with existing assignments or shifts cannot be deleted."
    );

    if (!confirmed) return;

    setSaving(true);
    setDeletingId(person.staff_id);

    setMessage("");
    setStaffError("");

    try {
      await api.delete(
        `/staff/members/${encodeURIComponent(person.staff_id)}`
      );

      setMessage(
        `Staff member ${person.staff_id} deleted from SQLite.`
      );

      await Promise.all([
        loadStaff(false),
        loadShifts(false),
      ]);
    } catch (error) {
      setStaffError(
        getApiError(
          error,
          "Unable to delete staff member."
        )
      );
    } finally {
      setSaving(false);
      setDeletingId(null);
    }
  }

  // ==========================================================
  // OPEN SHIFT EDIT FORM
  // ==========================================================

  function handleEditShift(shift) {
    if (!isAdmin) return;

    setEditingShift(shift);

    setShiftEditForm({
      shift_date: shift.shift_date,
      shift_start_time: minuteToTime(shift.start_minute),
      shift_end_time: minuteToTime(shift.end_minute),
    });

    setMessage("");
    setShiftError("");
  }

  // ==========================================================
  // SAVE SHIFT CHANGES
  // ==========================================================

  async function handleSaveShift(event) {
    event.preventDefault();

    if (!isAdmin || !editingShift || !shiftEditForm || saving) {
      return;
    }

    setMessage("");
    setShiftError("");

    const timingError = validateShiftTimes(
      shiftEditForm.shift_start_time,
      shiftEditForm.shift_end_time
    );

    if (timingError) {
      setShiftError(timingError);
      return;
    }

    setSaving(true);

    try {
      const payload = {
        shift_date: shiftEditForm.shift_date,
        shift_start_time: shiftEditForm.shift_start_time,
        shift_end_time: shiftEditForm.shift_end_time,
      };

      await api.put(
        `/staff/shifts/${editingShift.id}`,
        payload
      );

      const updatedStaffId = editingShift.staff_id;

      setEditingShift(null);
      setShiftEditForm(null);

      setMessage(
        `Shift timings updated successfully for ${updatedStaffId}.`
      );

      await loadShifts(false);
    } catch (error) {
      setShiftError(
        getApiError(
          error,
          "Unable to update staff shift."
        )
      );
    } finally {
      setSaving(false);
    }
  }

  // ==========================================================
  // MAIN UI
  // ==========================================================

  return (
    <div className="space-y-6 p-6">

      {/* ======================================================
          PAGE HEADER
      ====================================================== */}

      <section>
        <div className="flex items-center gap-3">
          <Users size={28} className="text-sky-400" />

          <div>
            <h1 className="text-2xl font-bold text-white">
              Staff Allocation
            </h1>

            <p className="mt-1 text-sm text-slate-400">
              Manage staff records, shifts, availability, and
              operational assignments.
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-sky-800 bg-slate-900 p-5">
        <h2 className="mb-3 text-lg font-semibold text-white">Airport Selection</h2>
        <AirportPicker label="Filter staff and shifts by airport" allowAll
          value={selectedAirport} onChange={setSelectedAirport} />
        <p className="mt-2 text-xs text-slate-400">
          {selectedAirport ? `Showing ${selectedAirport} staff and shifts.` : "Showing all airports, including unassigned staff."}
        </p>
      </section>

      {/* ======================================================
          STAFF API STATUS
      ====================================================== */}

      <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-700 bg-slate-900 p-4 text-sm">

        <div role="status">
          {staffLoading ? (
            <p className="text-sky-400">
              Loading staff records from SQLite...
            </p>
          ) : staffError ? (
            <p className="text-red-400">
              Staff API Error: {staffError}
            </p>
          ) : (
            <p className="text-emerald-400">
              SQLite Staff API Connected — {databaseStaff.length} records loaded.
              {isAdmin
                ? " Admin access."
                : " Read-only staff directory."}
            </p>
          )}
        </div>

        <button
          type="button"
          disabled={staffLoading || shiftsLoading || saving}
          onClick={() => {
            loadStaff();
            loadShifts();
          }}
          className={`${buttonStyle} border border-slate-700 bg-slate-800 text-white hover:bg-slate-700`}
        >
          <RefreshCw size={16} />
          Refresh Staff
        </button>

      </section>

      {/* ======================================================
          SUCCESS MESSAGE
      ====================================================== */}

      {message && (
        <div
          role="status"
          className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300"
        >
          {message}
        </div>
      )}

      {/* ======================================================
          STAFF STATISTICS
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">

        <SummaryCard
          title="Total Staff"
          value={statistics.total}
          icon={Users}
          color="text-sky-400"
        />

        <SummaryCard
          title="Active Employees"
          value={statistics.active}
          icon={UserCheck}
          color="text-emerald-400"
        />

        <SummaryCard
          title="Inactive Employees"
          value={statistics.inactive}
          icon={UserX}
          color="text-slate-400"
        />

      </section>

      {/* ======================================================
          STAFF MANAGEMENT
      ====================================================== */}

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">

        <div className="flex flex-wrap items-center justify-between gap-4">

          <div>
            <h2 className="text-xl font-bold text-white">
              Staff Management
            </h2>

            <p className="mt-1 text-sm text-slate-400">
              {isAdmin
                ? "Add staff with an initial shift, edit staff details, and manage records."
                : "Staff records are read-only for your account."}
            </p>
          </div>

          {isAdmin && (
            <button
              type="button"
              disabled={saving}
              onClick={() => {
                setShowAddForm((previous) => !previous);
                setStaffError("");
              }}
              className={`${buttonStyle} bg-sky-600 text-white hover:bg-sky-500`}
            >
              <UserPlus size={17} />
              {showAddForm ? "Close Form" : "Add Staff"}
            </button>
          )}

        </div>

        {/* ====================================================
            ADD STAFF FORM
        ==================================================== */}

        {isAdmin && showAddForm && (
          <form
            onSubmit={handleAddStaff}
            className="mt-5 grid gap-4 border-t border-slate-800 pt-5 md:grid-cols-2"
          >

            <StaffFields
              form={newStaff}
              setForm={setNewStaff}
              includeId
              disabled={saving}
            />

            <div className="md:col-span-2">
              <AirportPicker label="Staff Airport (Required) *"
                value={newStaff.airport_code}
                onChange={(airport_code) => setNewStaff((previous) => ({ ...previous, airport_code }))}
                disabled={saving} />
            </div>

            {/* INITIAL SHIFT */}

            <div className="md:col-span-2 mt-3 border-t border-slate-800 pt-5">

              <div className="flex items-center gap-2">
                <Clock3 size={20} className="text-sky-400" />

                <h3 className="text-lg font-semibold text-white">
                  Initial Shift (Required)
                </h3>
              </div>

              <p className="mt-2 text-sm text-slate-400">
                Every new staff member must be assigned an initial
                shift date and timings.
              </p>

              <p className="mt-1 text-xs text-slate-500">
                For overnight shifts, select an end time earlier
                than the start time. For example, 22:00 to 06:00.
              </p>

            </div>

            <ShiftFields
              form={newStaff}
              setForm={setNewStaff}
              disabled={saving}
            />

            {staffError && (
              <div className="md:col-span-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                {staffError}
              </div>
            )}

            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={saving}
                className={`${buttonStyle} bg-emerald-600 text-white hover:bg-emerald-500`}
              >
                <Save size={17} />
                {saving
                  ? "Saving..."
                  : "Save Staff With Initial Shift"}
              </button>
            </div>

          </form>
        )}

      </section>

      {/* ======================================================
          STAFF MONITORING
      ====================================================== */}

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">

        <div className="mb-5 flex flex-wrap items-center justify-between gap-4">

          <div>
            <h2 className="text-xl font-bold text-white">
              Staff Monitoring
            </h2>

            <p className="mt-1 text-sm text-slate-400">
              Employment status is not the same as real-time availability.
            </p>
          </div>

          <p className="text-sm text-slate-400">
            Showing {filteredStaff.length} of {databaseStaff.length} staff
          </p>

        </div>

        {/* SEARCH AND FILTER */}

        <div className="mb-5 flex flex-wrap gap-3">

          <div className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3">

            <Search size={18} className="text-slate-400" />

            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search staff ID, name, role..."
              aria-label="Search staff"
              className="w-full bg-transparent py-3 text-sm text-white outline-none placeholder:text-slate-500"
            />

          </div>

          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            aria-label="Filter by employment status"
            className={inputStyle}
          >
            <option value="All">
              All Employment Statuses
            </option>

            {EMPLOYMENT_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status === "active" ? "Active" : "Inactive"}
              </option>
            ))}
          </select>

        </div>

        {/* STAFF TABLE */}

        <div className="overflow-x-auto">

          <table className="w-full min-w-[680px] text-left text-sm">

            <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3">Staff Member</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Employment Status</th>
                <th className="px-4 py-3">Airport</th>

                {isAdmin && (
                  <th className="px-4 py-3">Actions</th>
                )}
              </tr>
            </thead>

            <tbody>
              {filteredStaff.map((person) => (
                <tr
                  key={person.staff_id}
                  className="border-b border-slate-800/70 transition hover:bg-slate-800/40"
                >

                  <td className="px-4 py-4">
                    <p className="font-semibold text-white">
                      {person.full_name}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {person.staff_id}
                    </p>
                  </td>

                  <td className="px-4 py-4 text-slate-300">
                    {person.role}
                  </td>

                  <td className="px-4 py-4">
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        person.employment_status === "active"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-slate-500/10 text-slate-400"
                      }`}
                    >
                      {person.employment_status === "active"
                        ? "Active"
                        : "Inactive"}
                    </span>
                  </td>

                  <td className="px-4 py-4 text-slate-300">{person.airport_code || "Unassigned"}</td>

                  {isAdmin && (
                    <td className="px-4 py-4">

                      <div className="flex flex-wrap gap-2">

                        <button
                          type="button"
                          disabled={saving}
                          onClick={() => handleEditStaff(person)}
                          className="inline-flex items-center gap-2 rounded-lg border border-sky-500/30 px-3 py-2 text-xs text-sky-400 hover:bg-sky-500/10 disabled:opacity-50"
                        >
                          <Pencil size={14} />
                          Edit
                        </button>

                        <button
                          type="button"
                          disabled={saving}
                          onClick={() => handleDeleteStaff(person)}
                          className="inline-flex items-center gap-2 rounded-lg border border-red-500/30 px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                        >
                          <Trash2 size={14} />
                          {deletingId === person.staff_id
                            ? "Deleting..."
                            : "Delete"}
                        </button>

                      </div>

                    </td>
                  )}

                </tr>
              ))}
            </tbody>

          </table>

          {!staffLoading && filteredStaff.length === 0 && (
            <div className="py-8 text-center text-sm text-slate-400">
              {staffError
                ? "Unable to display staff records."
                : "No staff records match your filters."}
            </div>
          )}

        </div>

      </section>

      {/* ======================================================
          SHIFT MANAGEMENT
      ====================================================== */}

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">

        <div className="mb-5 flex flex-wrap items-center justify-between gap-4">

          <div>
            <div className="flex items-center gap-2">
              <Clock3 size={22} className="text-sky-400" />

              <h2 className="text-xl font-bold text-white">
                Shift Management
              </h2>
            </div>

            <p className="mt-2 text-sm text-slate-400">
              {isAdmin
                ? "View and modify staff shift dates and timings."
                : "View scheduled staff shifts. Editing is restricted to Admin."}
            </p>
          </div>

          <button
            type="button"
            disabled={shiftsLoading || saving}
            onClick={() => loadShifts()}
            className={`${buttonStyle} border border-slate-700 bg-slate-800 text-white hover:bg-slate-700`}
          >
            <RefreshCw size={16} />
            Refresh Shifts
          </button>

        </div>

        {/* SHIFT ERROR */}

        {shiftError && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
            Shift API Error: {shiftError}
          </div>
        )}

        {/* SHIFT SEARCH */}

        <div className="mb-5 flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3">

          <Search size={18} className="text-slate-400" />

          <input
            type="text"
            value={shiftSearch}
            onChange={(event) => setShiftSearch(event.target.value)}
            placeholder="Search shifts by staff ID, name, role, or date..."
            aria-label="Search staff shifts"
            className="w-full bg-transparent py-3 text-sm text-white outline-none placeholder:text-slate-500"
          />

        </div>

        {/* SHIFT TABLE */}

        <div className="overflow-x-auto">

          <table className="w-full min-w-[760px] text-left text-sm">

            <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">

              <tr>
                <th className="px-4 py-3">Staff Member</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Shift Date</th>
                <th className="px-4 py-3">Start Time</th>
                <th className="px-4 py-3">End Time</th>
                <th className="px-4 py-3">Shift Type</th>

                {isAdmin && (
                  <th className="px-4 py-3">Actions</th>
                )}
              </tr>

            </thead>

            <tbody>

              {filteredShifts.map((shift) => (
                <tr
                  key={shift.id}
                  className="border-b border-slate-800/70 transition hover:bg-slate-800/40"
                >

                  <td className="px-4 py-4">

                    <p className="font-semibold text-white">
                      {shift.full_name || shift.staff_id}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {shift.staff_id}
                    </p>

                  </td>

                  <td className="px-4 py-4 text-slate-300">
                    {shift.role || "—"}
                  </td>

                  <td className="px-4 py-4 text-slate-300">
                    {shift.shift_date}
                  </td>

                  <td className="px-4 py-4 text-slate-300">
                    {minuteToTime(shift.start_minute)}
                  </td>

                  <td className="px-4 py-4 text-slate-300">
                    {minuteToTime(shift.end_minute)}
                  </td>

                  <td className="px-4 py-4">

                    {isOvernightShift(shift) ? (
                      <span className="rounded-full bg-violet-500/10 px-3 py-1 text-xs font-semibold text-violet-400">
                        Overnight
                      </span>
                    ) : (
                      <span className="rounded-full bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-400">
                        Day Shift
                      </span>
                    )}

                  </td>

                  {isAdmin && (
                    <td className="px-4 py-4">

                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => handleEditShift(shift)}
                        className="inline-flex items-center gap-2 rounded-lg border border-sky-500/30 px-3 py-2 text-xs text-sky-400 hover:bg-sky-500/10 disabled:opacity-50"
                      >
                        <Pencil size={14} />
                        Edit Shift
                      </button>

                    </td>
                  )}

                </tr>
              ))}

            </tbody>

          </table>

          {shiftsLoading && (
            <div className="py-8 text-center text-sm text-sky-400">
              Loading staff shifts...
            </div>
          )}

          {!shiftsLoading &&
            !shiftError &&
            filteredShifts.length === 0 && (
              <div className="py-8 text-center text-sm text-slate-400">
                No staff shifts match your search.
              </div>
            )}

        </div>

      </section>

      {/* ======================================================
          EXISTING STAFF TOOLS — PRESERVED
      ====================================================== */}

      <StaffAvailabilityChecker />

      <StaffAllocationForm />

      {/* Staff assignment history — accessible to authenticated staff.
          The history API enforces Admin-only unknown-airport records. */}
      <StaffAssignmentHistory />

      {/* ======================================================
          EDIT STAFF MODAL
      ====================================================== */}

      {isAdmin && editingStaff && editForm && (

        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">

          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-staff-title"
            className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
          >

            <div className="mb-5 flex items-center justify-between">

              <h2
                id="edit-staff-title"
                className="text-xl font-bold text-white"
              >
                Edit Staff — {editingStaff}
              </h2>

              <button
                type="button"
                disabled={saving}
                onClick={() => {
                  setEditingStaff(null);
                  setEditForm(null);
                }}
                aria-label="Close edit staff form"
                className="text-slate-400 hover:text-white disabled:opacity-50"
              >
                <X size={22} />
              </button>

            </div>

            <form
              onSubmit={handleSaveEdit}
              className="space-y-4"
            >

              <StaffFields
                form={editForm}
                setForm={setEditForm}
                disabled={saving}
              />

              <div className="flex justify-end gap-3 pt-3">

                <button
                  type="button"
                  disabled={saving}
                  onClick={() => {
                    setEditingStaff(null);
                    setEditForm(null);
                  }}
                  className={`${buttonStyle} border border-slate-700 text-slate-300 hover:bg-slate-800`}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={saving}
                  className={`${buttonStyle} bg-sky-600 text-white hover:bg-sky-500`}
                >
                  <Save size={17} />
                  {saving ? "Saving..." : "Save Changes"}
                </button>

              </div>

            </form>

          </div>

        </div>
      )}

      {/* ======================================================
          EDIT SHIFT MODAL
      ====================================================== */}

      {isAdmin && editingShift && shiftEditForm && (

        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">

          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-shift-title"
            className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
          >

            <div className="mb-5 flex items-center justify-between">

              <div>

                <h2
                  id="edit-shift-title"
                  className="text-xl font-bold text-white"
                >
                  Edit Staff Shift
                </h2>

                <p className="mt-1 text-sm text-slate-400">
                  Staff ID: {editingShift.staff_id}
                </p>

              </div>

              <button
                type="button"
                disabled={saving}
                onClick={() => {
                  setEditingShift(null);
                  setShiftEditForm(null);
                }}
                aria-label="Close edit shift form"
                className="text-slate-400 hover:text-white disabled:opacity-50"
              >
                <X size={22} />
              </button>

            </div>

            <form
              onSubmit={handleSaveShift}
              className="space-y-4"
            >

              <ShiftFields
                form={shiftEditForm}
                setForm={setShiftEditForm}
                disabled={saving}
              />

              <p className="text-xs text-slate-400">
                Overnight shifts are supported. For example,
                22:00 to 06:00 represents a shift ending the
                following day.
              </p>

              {shiftError && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                  {shiftError}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-3">

                <button
                  type="button"
                  disabled={saving}
                  onClick={() => {
                    setEditingShift(null);
                    setShiftEditForm(null);
                  }}
                  className={`${buttonStyle} border border-slate-700 text-slate-300 hover:bg-slate-800`}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={saving}
                  className={`${buttonStyle} bg-sky-600 text-white hover:bg-sky-500`}
                >
                  <Save size={17} />
                  {saving ? "Saving..." : "Save Shift Changes"}
                </button>

              </div>

            </form>

          </div>

        </div>
      )}

    </div>
  );
}