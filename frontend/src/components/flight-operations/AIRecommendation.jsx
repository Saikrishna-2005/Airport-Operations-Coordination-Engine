import React, { useEffect, useState } from 'react';
import { Sparkles, AlertOctagon, RefreshCw, ShieldCheck } from 'lucide-react';
import { generateAIPlanning } from '../../services/flightApi';
import AgentWorkflow from './AgentWorkflow';

const Section = ({ title, items }) => (
  <section className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
    <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-cyan-300">{title}</h4>
    {Array.isArray(items) && items.length ? (
      <ol className="list-decimal space-y-1 pl-5 text-xs leading-relaxed text-slate-300">
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ol>
    ) : (
      <p className="text-xs text-slate-500">Not provided by the planning agent.</p>
    )}
  </section>
);

const displayValue = (value, suffix = '') =>
  value === null || value === undefined ? 'Unknown' : `${value}${suffix}`;

/** Live Gemini planning. Displays advisory evidence; never executes operational actions. */
export const AIRecommendation = ({ flight, onActionComplete }) => {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [runwayCode, setRunwayCode] = useState('');

  const flightId = flight?.id;
  const flightNumber = flight?.flightNumber ?? flight?.flight_number;

  useEffect(() => {
    setResult(null);
    setError('');
    setRunwayCode('');
  }, [flightId, flightNumber]);

  const generate = async () => {
    if (!flight || loading) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await generateAIPlanning(flight, { runwayCode });
      setResult(response);
      if (onActionComplete) onActionComplete(response);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : err?.message || 'AI planning request failed.');
    } finally {
      setLoading(false);
    }
  };

  const plan = result?.planning_result;
  const operational = result?.rule_results?.[0];
  const inputs = operational?.operational_inputs;
  const sources = operational?.input_sources;
  const weather = operational?.weather_metadata;
  const runway = operational?.runway_metadata;
  const rules = operational?.results ?? [];

  return (
    <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-cyan-400" />
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">Gemini Operational Planning</h3>
            <p className="text-xs text-slate-400">Advisory plan · human review required</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="ai-runway-code" className="text-xs text-slate-300">Runway (optional)</label>
          <input
            id="ai-runway-code"
            type="text"
            value={runwayCode}
            onChange={(event) => setRunwayCode(event.target.value.toUpperCase())}
            placeholder="e.g. 09L"
            maxLength={10}
            disabled={loading}
            className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white placeholder:text-slate-500"
          />
          <button
            type="button"
            onClick={generate}
            disabled={!flight || loading}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-3 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Generating...' : result ? 'Regenerate Plan' : 'Generate AI Plan'}
          </button>
        </div>
      </div>

      {!result && !loading && !error && (
        <p className="text-xs text-slate-400">
          Generate a live planning assessment for {flightNumber || 'the selected flight'}.
          Leave the runway blank if its identifier is unknown. No operational action will be executed.
        </p>
      )}
      {error && <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">{error}</div>}

      {plan && (
        <>
          <div className="rounded-lg border border-cyan-800/40 bg-slate-950/70 p-4">
            <p className="mb-1 text-[11px] font-mono text-cyan-400">{result.workflow_id} · {plan.airport}</p>
            <h4 className="text-sm font-semibold text-white">Planning Objective</h4>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">{plan.planning_objective}</p>
            <span className="mt-3 inline-flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-300">
              <AlertOctagon className="h-3 w-3" /> Pending human review
            </span>
          </div>

          <section className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
            <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-cyan-300">Operational Assessment</h4>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-slate-800 p-3">
                <p className="text-xs text-slate-400">Flight Delay</p>
                <p className="mt-1 text-lg font-semibold text-white">{displayValue(inputs?.delay_minutes, ' min')}</p>
                <p className="mt-1 text-[11px] text-slate-500">{sources?.delay_minutes ?? 'Unknown source'}</p>
              </div>
              <div className="rounded-lg border border-slate-800 p-3">
                <p className="text-xs text-slate-400">Rainfall</p>
                <p className="mt-1 text-lg font-semibold text-white">{displayValue(inputs?.rainfall_mm, ' mm')}</p>
                <p className="mt-1 text-[11px] text-slate-500">{weather?.source ?? 'Unknown source'}</p>
                {weather?.observation_age_minutes != null && (
                  <p className="mt-1 text-[11px] text-slate-500">Observed {weather.observation_age_minutes} minutes before evaluation</p>
                )}
              </div>
              <div className="rounded-lg border border-slate-800 p-3">
                <p className="text-xs text-slate-400">Runway {runway?.runway_code ?? ''}</p>
                <p className="mt-1 text-lg font-semibold text-white">{runway?.status ?? 'UNKNOWN'}</p>
                <p className="mt-1 text-[11px] text-amber-300">
                  {runway?.verified ? 'Reported verified' : 'Not independently verified'}
                </p>
                {runway?.age_minutes != null && (
                  <p className="mt-1 text-[11px] text-slate-500">Report age: {runway.age_minutes} min</p>
                )}
                {runway?.reason && <p className="mt-1 text-[11px] text-slate-500">{runway.reason}</p>}
              </div>
            </div>

            <div className="mt-4 space-y-2">
              <h5 className="text-xs font-semibold text-slate-200">Rule Evaluation</h5>
              {rules.length ? rules.map((rule) => (
                <div key={rule.rule_id} className="rounded-lg border border-slate-800 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-white">{rule.rule_id} — {rule.rule_name}</span>
                    <span className={`text-[11px] ${rule.triggered ? 'text-rose-300' : 'text-amber-300'}`}>
                      {rule.evaluation_status === 'NOT_EVALUATED'
                        ? 'NOT EVALUATED'
                        : rule.triggered ? `${rule.severity} RISK` : 'NOT TRIGGERED'}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-400">{rule.message}</p>
                </div>
              )) : <p className="text-xs text-slate-500">No rule results provided.</p>}
            </div>
          </section>

          <Section title="Research Requirements" items={plan.research_requirements} />
          <Section title="Analysis Requirements" items={plan.analysis_requirements} />
          <Section title="Resource Requirements" items={plan.resource_requirements} />
          <Section title="Proposed Steps" items={plan.proposed_steps} />
          <AgentWorkflow planningResponse={result} />

          <div className="flex items-start gap-2 rounded-lg border border-amber-800/40 bg-amber-950/20 p-3 text-xs text-amber-200">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Advisory only. Flight delays come from SQLite, rainfall from Open-Meteo, and runway
              availability from manual reports when provided. Manual runway reports are unverified;
              weather data is not an official aviation observation. No operational approval or
              execution is performed by this component.
            </span>
          </div>
        </>
      )}
    </div>
  );
};

export default AIRecommendation;
