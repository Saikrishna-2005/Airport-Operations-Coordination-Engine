import { useState } from "react";
import { DoorOpen, Search, AlertTriangle, CheckCircle } from "lucide-react";
import api from "../api";

export default function Resources() {
  const [form, setForm] = useState({
    airport_code: "HYD",
    flight_number: "",
    gate_id: "",
    start_time: "",
    end_time: "",
    candidate_gates: "G1, G2, G3",
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    setResult(null);
    setError("");
  };

  const convertToMinutes = (time) => {
    const [hours, minutes] = time.split(":").map(Number);
    return hours * 60 + minutes;
  };

  const handleCheckAvailability = async (event) => {
    event.preventDefault();

    setError("");
    setResult(null);

    const startMinute = convertToMinutes(form.start_time);
    const endMinute = convertToMinutes(form.end_time);

    if (endMinute <= startMinute) {
      setError(
        "End time must be later than start time. Overnight bookings are not supported yet."
      );
      return;
    }

    const candidateGates = [
      ...new Set(
        form.candidate_gates
          .split(",")
          .map((gate) => gate.trim().toUpperCase())
          .filter(Boolean)
      ),
    ];

    if (candidateGates.length > 50) {
      setError("You can provide a maximum of 50 candidate gates.");
      return;
    }

    const requestData = {
      airport_code: form.airport_code.trim().toUpperCase(),
      flight_number: form.flight_number.trim().toUpperCase(),
      gate_id: form.gate_id.trim().toUpperCase(),
      start_minute: startMinute,
      end_minute: endMinute,
      candidate_gates: candidateGates,
    };

    try {
      setLoading(true);

      const response = await api.post(
        "/gates/availability",
        requestData
      );

      setResult(response.data);
    } catch (err) {
      const status = err.response?.status;

      if (status === 401) {
        setError("Your session has expired. Please log in again.");
      } else if (status === 403) {
        setError("You do not have permission to check gate availability.");
      } else if (status === 422) {
        setError("Invalid gate information. Please check your inputs.");
      } else {
        setError(
          "Unable to check gate availability. Please verify the backend connection."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <DoorOpen size={28} className="text-sky-400" />

        <div>
          <h2 className="text-2xl font-bold text-white">
            Gates & Resources
          </h2>

          <p className="text-sm text-slate-400">
            Check gate scheduling conflicts and alternative gate candidates.
          </p>
        </div>
      </div>

      {/* Gate Availability Form */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h3 className="mb-5 text-lg font-semibold text-white">
          Gate Availability Checker
        </h3>

        <form
          onSubmit={handleCheckAvailability}
          className="grid grid-cols-1 gap-4 md:grid-cols-2"
        >
          {/* Airport Code */}
          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Airport Code
            </label>

            <input
              type="text"
              name="airport_code"
              value={form.airport_code}
              onChange={handleChange}
              minLength={3}
              maxLength={3}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-white"
              placeholder="HYD"
            />
          </div>

          {/* Flight Number */}
          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Flight Number
            </label>

            <input
              type="text"
              name="flight_number"
              value={form.flight_number}
              onChange={handleChange}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-white"
              placeholder="AI503"
            />
          </div>

          {/* Gate ID */}
          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Requested Gate
            </label>

            <input
              type="text"
              name="gate_id"
              value={form.gate_id}
              onChange={handleChange}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-white"
              placeholder="G1"
            />
          </div>

          {/* Candidate Gates */}
          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Alternative Gate Candidates
            </label>

            <input
              type="text"
              name="candidate_gates"
              value={form.candidate_gates}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-white"
              placeholder="G1, G2, G3"
            />
          </div>

          {/* Start Time */}
          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Start Time
            </label>

            <input
              type="time"
              name="start_time"
              value={form.start_time}
              onChange={handleChange}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-white"
            />
          </div>

          {/* End Time */}
          <div>
            <label className="mb-2 block text-sm text-slate-300">
              End Time
            </label>

            <input
              type="time"
              name="end_time"
              value={form.end_time}
              onChange={handleChange}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-white"
            />
          </div>

          {/* Submit Button */}
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-3 font-semibold text-white hover:bg-sky-700 disabled:opacity-50"
            >
              <Search size={18} />

              {loading ? "Checking..." : "Check Gate Availability"}
            </button>
          </div>
        </form>
      </div>

      {/* Error Message */}
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-700 bg-red-950 p-4 text-red-300"
        >
          <AlertTriangle className="mb-2" size={22} />
          {error}
        </div>
      )}

      {/* Gate Availability Result */}
      {result && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="mb-4 text-lg font-semibold text-white">
            Gate Availability Result
          </h3>

          <div className="mb-4 text-sm text-slate-300">
            <p>
              <strong>Airport:</strong> {result.airport_code}
            </p>

            <p>
              <strong>Flight:</strong> {result.flight_number}
            </p>

            <p>
              <strong>Requested Gate:</strong> {result.gate_id}
            </p>
          </div>

          {/* Available Gate */}
          {result.available ? (
            <div className="flex items-center gap-3 rounded-lg border border-green-700 bg-green-950 p-4 text-green-300">
              <CheckCircle size={24} />

              <div>
                <p className="font-semibold">
                  No Scheduling Conflict Found
                </p>

                <p className="text-sm">
                  Gate {result.gate_id} has no overlapping booking
                  in the current database records.
                </p>
              </div>
            </div>
          ) : (
            /* Gate Conflict */
            <div className="rounded-lg border border-red-700 bg-red-950 p-4">
              <div className="mb-3 flex items-center gap-3 text-red-300">
                <AlertTriangle size={24} />

                <p className="font-semibold">
                  Gate Scheduling Conflict Detected
                </p>
              </div>

              <p className="text-sm text-slate-300">
                Gate {result.gate_id} conflicts with:
              </p>

              <ul className="mt-2 list-disc pl-6 text-red-300">
                {result.conflicting_flights.map((flight) => (
                  <li key={flight}>{flight}</li>
                ))}
              </ul>

              {/* Alternative Gates */}
              <div className="mt-5">
                <h4 className="font-semibold text-white">
                  Alternative Gate Candidates
                </h4>

                {result.alternative_gates.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {result.alternative_gates.map((gate) => (
                      <span
                        key={gate}
                        className="rounded-lg border border-sky-700 bg-sky-950 px-4 py-2 text-sky-300"
                      >
                        {gate}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-amber-400">
                    No conflict-free alternative found among the supplied candidates.
                  </p>
                )}
              </div>
            </div>
          )}

          <p className="mt-4 text-xs text-amber-400">
            Advisory result only. Gate inventory, aircraft compatibility,
            and operational approval must be verified separately.
          </p>
        </div>
      )}
    </div>
  );
}