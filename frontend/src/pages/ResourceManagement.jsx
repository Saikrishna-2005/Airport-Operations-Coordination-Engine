import { Link } from "react-router-dom";
import { Layers, ArrowUpRight, AlertTriangle } from "lucide-react";
import AirportBoard from "./AirportBoard";

export default function ResourceManagement() {
  return (
    <div className="space-y-6 p-6">
      <section className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Layers size={28} className="text-sky-400" />
            <h1 className="text-2xl font-bold text-white">Resource Management</h1>
          </div>
          <p className="mt-2 text-sm text-slate-400">
            Monitor DEL flight reports, reported gate assignments and local runway reports.
          </p>
        </div>
        <Link to="/resources" className="flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500">
          Gate Availability Checker <ArrowUpRight size={16} />
        </Link>
      </section>
      <section className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
        <AlertTriangle size={20} className="shrink-0 text-amber-400" />
        <div>
          <p className="font-semibold text-amber-400">Resource information and limitations</p>
          <p className="mt-1 text-sm text-slate-300">
            Flight and gate reports follow the backend data mode. Reported gate assignments do not establish occupancy or availability. The gate conflict checker uses separate local database records. Runway reports are manual and unverified. Refresh only when needed to conserve API quota.
          </p>
        </div>
      </section>
      <AirportBoard airport="DEL" />
    </div>
  );
}
