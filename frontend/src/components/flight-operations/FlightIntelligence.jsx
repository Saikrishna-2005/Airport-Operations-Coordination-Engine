import React, { useEffect, useRef, useState } from "react";
import { getFlightIntelligence } from "../../services/flightApi";

const show = (value) => value == null || value === "" ? "Unavailable" : String(value);
const utc = (value) => {
  if (value == null || value === "") return "Unavailable";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? show(value) : d.toISOString().replace("T", " ").replace(/\.\d+Z$/, " UTC");
};
const errorText = (err) => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(x => x.msg || "Invalid input").join("; ");
  return err?.message || "Flight intelligence request failed.";
};
const inputClass = "mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-white";
const statusStyle = { delayed: "text-amber-300", cancelled: "text-rose-300", scheduled: "text-cyan-300", active: "text-emerald-300", landed: "text-emerald-300", diverted: "text-amber-300" };

function Field({ flight, group, name, label, time = false, unit = "" }) {
  const value = flight[group]?.[name];
  const source = flight.field_sources?.[`${group}.${name}`];
  const display = name === "on_ground" && typeof value === "boolean" ? (value ? "Yes" : "No") : time ? utc(value) : show(value);
  return <div className="rounded-lg bg-slate-950 p-2 break-words">
    <div className="text-slate-400">{label}</div>
    <div className="mt-1 font-semibold text-slate-100">{display}{value != null && value !== "" ? unit : ""}</div>
    {source && <div className="mt-1 text-[10px] text-slate-400">{source.provider} · {utc(source.data_timestamp)}</div>}
  </div>;
}

export function FlightIntelligence({ airport = "DEL" }) {
  const [code, setCode] = useState(airport);
  const [identifiers, setIdentifiers] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const request = useRef(null);
  useEffect(() => { setCode(airport); }, [airport]);
  useEffect(() => () => { request.current?.abort(); request.current = null; }, []);
  const search = async (event) => {
    event.preventDefault();
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true); setError(null); setResult(null);
    try {
      const payload = await getFlightIntelligence({ airportCode: code, flightIdentifiers: identifiers.split(/[\s,]+/).filter(Boolean), signal: controller.signal });
      if (request.current === controller && !controller.signal.aborted) setResult(payload);
    } catch (err) {
      if (request.current === controller && !controller.signal.aborted) setError(errorText(err));
    } finally {
      if (request.current === controller) { setLoading(false); request.current = null; }
    }
  };
  const flights = result?.flights || [];
  const providers = [...new Set(flights.flatMap(f => f.providers || []))];
  return <section className="rounded-2xl border border-cyan-900/60 bg-slate-900/70 p-4 lg:p-5 space-y-4 text-xs">
    <div className="flex flex-wrap justify-between gap-2">
      <div><h2 className="text-sm font-bold text-white">Multi-Provider Flight Intelligence</h2><p className="mt-1 text-slate-400">OpenSky tracking + Cirium operational information</p></div>
      <span className="rounded-lg border border-amber-500/30 px-3 py-2 text-amber-300">{result ? `${result.data_mode.toUpperCase()} MODE` : "Mode determined by backend"}</span>
    </div>
    <form onSubmit={search} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <label className="text-slate-400">Airport (IATA / ICAO)<input className={inputClass} value={code} onChange={e => setCode(e.target.value.toUpperCase())} maxLength={4} required /></label>
      <label className="text-slate-400">Flight identifiers (up to 10)<input className={inputClass} value={identifiers} onChange={e => setIdentifiers(e.target.value)} placeholder="AI101, 6E204, AI306" required /></label>
      <button type="submit" disabled={loading} className="self-end rounded-lg bg-cyan-700 p-2 font-bold text-white disabled:opacity-50">{loading ? "Searching…" : "Search flight intelligence"}</button>
    </form>
    {error && <p role="alert" className="rounded-lg bg-rose-950 p-3 text-rose-300">{error}</p>}
    {result && <div className="space-y-3" aria-live="polite">
      <p className="text-slate-400">Results for {result.airport_code} · {flights.filter(f => f.status === "found").length} of {flights.length} found · {providers.length} contributing providers</p>
      {result.data_mode === "synthetic" && <p className="rounded-lg bg-amber-950 p-3 text-amber-300">Synthetic demonstration data — not real flight observations.</p>}
      {result.errors?.map((e,i) => <p key={i} className="rounded-lg bg-rose-950 p-2 text-rose-300">{e.tool}: {e.code} — {e.message}</p>)}
      {!flights.length && <p>No flight records returned.</p>}
      {flights.map(f => { const op = f.operational_data || {}; return <article key={f.requested_identifier} className="space-y-3 rounded-xl border border-slate-700 p-3">
        <div className="flex flex-wrap justify-between gap-2"><div><h3 className="text-base font-bold text-white">{f.requested_identifier} · {show(op.airline)}</h3><p className="text-slate-400">{show(op.origin_airport)} → {show(op.destination_airport)} · Lookup: {f.status}</p></div><strong className={statusStyle[op.status] || "text-slate-300"}>{show(op.status)}</strong></div>
        <p className="text-cyan-300">Providers: {(f.providers || []).join(", ") || "None"}</p>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {[["baro_altitude","Altitude"," m"],["velocity","Speed"," m/s"],["on_ground","On ground",""],["true_track","Heading","°"]].map(([name,label,unit]) => <Field key={name} flight={f} group="data" name={name} label={label} unit={unit}/>) }
          {[["departure_delay_minutes","Departure delay"," min"],["arrival_delay_minutes","Arrival delay"," min"],["departure_gate","Departure gate",""],["arrival_gate","Arrival gate",""],["departure_terminal","Departure terminal",""],["arrival_terminal","Arrival terminal",""],["status","Operational status",""]].map(([name,label,unit]) => <Field key={name} flight={f} group="operational_data" name={name} label={label} unit={unit}/>)}
        </div>
        <details><summary className="cursor-pointer text-cyan-300">Flight timings (UTC)</summary><div className="mt-2 grid grid-cols-2 gap-2 lg:grid-cols-3">{["scheduled","estimated","actual"].flatMap(kind => ["departure","arrival"].map(direction => <Field key={`${kind}_${direction}`} flight={f} group="operational_data" name={`${kind}_${direction}`} label={`${kind} ${direction}`} time/>))}</div></details>
        {f.conflicts?.map((c,i) => <p key={i} className="rounded-lg bg-rose-950 p-2 text-rose-300">Conflict: {c.field_name} — {c.reason} ({c.resolved ? "resolved" : "unresolved"})</p>)}
        {!!f.missing_fields?.length && <details className="text-amber-300"><summary className="cursor-pointer">Unavailable fields ({f.missing_fields.length})</summary><p className="mt-1">Some timings may not apply yet or to cancelled flights.</p><ul className="mt-1 list-disc pl-5">{f.missing_fields.map(name => <li key={name}>{name.replace(/^operational_data\./, "").replaceAll("_", " ")}</li>)}</ul></details>}
        <details><summary className="cursor-pointer text-slate-400">Field-level provenance</summary><div className="mt-2 space-y-1 break-all text-slate-400">{Object.entries(f.field_sources || {}).map(([key,s]) => <p key={key}>{key}: {s.provider} · {utc(s.data_timestamp)} · {s.source_id}</p>)}</div></details>
      </article>; })}
    </div>}
    <p className="text-slate-500">Read-only advisory information. Gate assignments do not establish resource availability; tracking does not establish departure readiness.</p>
  </section>;
}
