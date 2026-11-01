import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Layers,
  DoorOpen,
  CheckCircle2,
  Plane,
  Wrench,
  Search,
  ArrowUpRight,
  AlertTriangle,
} from "lucide-react";

import { demoGates } from "../data/resourceDemoData";

export default function ResourceManagement() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");

  // Gate statistics from demonstration records.
  const totalGates = demoGates.length;

  const availableGates = demoGates.filter(
    (gate) => gate.status === "Available"
  ).length;

  const occupiedGates = demoGates.filter(
    (gate) => gate.status === "Occupied"
  ).length;

  const maintenanceGates = demoGates.filter(
    (gate) => gate.status === "Maintenance"
  ).length;

  // Filter demonstration gates by status and search text.
  const filteredGates = demoGates.filter((gate) => {
    const matchesStatus =
      filter === "All" || gate.status === filter;

    const query = search.trim().toLowerCase();

    const matchesSearch = [
      gate.id,
      gate.terminal,
      gate.flight,
      gate.route,
      gate.status,
    ].some((value) => value.toLowerCase().includes(query));

    return matchesStatus && matchesSearch;
  });

  const statusStyles = {
    Available: "bg-emerald-500/10 text-emerald-400",
    Occupied: "bg-amber-500/10 text-amber-400",
    Maintenance: "bg-red-500/10 text-red-400",
  };

  const summaryCards = [
    {
      title: "Total Gates",
      value: totalGates,
      icon: DoorOpen,
      color: "text-sky-400",
    },
    {
      title: "Available",
      value: availableGates,
      icon: CheckCircle2,
      color: "text-emerald-400",
    },
    {
      title: "Occupied",
      value: occupiedGates,
      icon: Plane,
      color: "text-amber-400",
    },
    {
      title: "Maintenance",
      value: maintenanceGates,
      icon: Wrench,
      color: "text-red-400",
    },
  ];

  return (
    <div className="space-y-6 p-6">

      {/* Page heading */}
      <section className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Layers size={28} className="text-sky-400" />

            <h1 className="text-2xl font-bold text-white">
              Resource Management
            </h1>
          </div>

          <p className="mt-2 text-sm text-slate-400">
            Monitor airport gate resources and availability.
          </p>
        </div>

        <Link
          to="/resources"
          className="flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500"
        >
          Gate Availability Checker
          <ArrowUpRight size={16} />
        </Link>
      </section>

      {/* Demo data warning */}
      <section className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
        <AlertTriangle
          size={20}
          className="shrink-0 text-amber-400"
        />

        <div>
          <p className="font-semibold text-amber-400">
            Demonstration Data
          </p>

          <p className="mt-1 text-sm text-slate-300">
            The gate monitoring records displayed below are
            illustrative sample data from the Resource Management
            module. They are not synchronized with the backend
            Gate Availability Checker.
          </p>
        </div>
      </section>

      {/* Gate summary cards */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map(({ title, value, icon: Icon, color }) => (
          <div
            key={title}
            className="rounded-xl border border-slate-800 bg-slate-900 p-5"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-400">{title}</p>

              <Icon size={22} className={color} />
            </div>

            <p className="mt-4 text-3xl font-bold text-white">
              {value}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              Sample gate records
            </p>
          </div>
        ))}
      </section>

      {/* Gate Monitoring */}
      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white">
              Gate Monitoring
            </h2>

            <p className="mt-1 text-sm text-slate-400">
              Search and filter sample airport gates.
            </p>
          </div>

          <p className="text-sm text-slate-400">
            Showing {filteredGates.length} of {totalGates} gates
          </p>
        </div>

        {/* Search */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3">
            <Search size={18} className="text-slate-400" />

            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search gates, flights, terminals..."
              aria-label="Search gates"
              className="w-full bg-transparent py-3 text-sm text-white outline-none placeholder:text-slate-500"
            />
          </div>

          {/* Status filters */}
          <div className="flex flex-wrap gap-2">
            {["All", "Available", "Occupied", "Maintenance"].map(
              (status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setFilter(status)}
                  aria-pressed={filter === status}
                  className={`rounded-lg px-3 py-2 text-sm transition ${
                    filter === status
                      ? "bg-sky-600 text-white"
                      : "border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  {status}
                </button>
              )
            )}
          </div>
        </div>

        {/* Gate cards */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredGates.map((gate) => (
            <article
              key={gate.id}
              className="rounded-xl border border-slate-800 bg-slate-900 p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-bold text-white">
                    Gate {gate.id}
                  </h3>

                  <p className="mt-1 text-xs text-slate-400">
                    {gate.terminal}
                  </p>
                </div>

                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    statusStyles[gate.status]
                  }`}
                >
                  {gate.status}
                </span>
              </div>

              <div className="mt-5 border-t border-slate-800 pt-4">
                <p className="font-semibold text-white">
                  {gate.flight}
                </p>

                <p className="mt-2 text-sm text-slate-400">
                  {gate.route}
                </p>

                <p className="mt-2 text-sm text-slate-400">
                  {gate.window}
                </p>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-slate-800 pt-4">
                <span className="text-xs text-slate-500">
                  Resource ID: {gate.id}
                </span>

                <span className="text-xs text-amber-400">
                  Demo record
                </span>
              </div>
            </article>
          ))}
        </div>

        {/* Empty search results */}
        {filteredGates.length === 0 && (
          <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-8 text-center">
            <p className="text-slate-400">
              No gates match your search or selected status.
            </p>
          </div>
        )}
      </section>

    </div>
  );
}