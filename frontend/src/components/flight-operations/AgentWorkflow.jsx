import React from 'react';
import { CheckCircle2, Clock, Cpu } from 'lucide-react';

/** Renders real planning pipeline results when provided; supports legacy workflow props. */
export const AgentWorkflow = ({ workflow = [], planningResponse = null }) => {
  const liveSteps = planningResponse ? [
    {
      stage: 'Gate Availability', agent: 'Gate Availability Tool',
      status: planningResponse.gate_result?.status === 'skipped' ? 'SKIPPED' : 'COMPLETED',
      detail: planningResponse.gate_result?.reason || (planningResponse.gate_result ? 'Gate check returned a result.' : 'No gate result returned.'),
    },
    {
      stage: 'Operational Planning', agent: 'Gemini Planning Agent',
      status: planningResponse.planning_result ? 'COMPLETED' : 'UNKNOWN',
      detail: planningResponse.planning_result?.planning_objective || 'No planning result returned.',
    },
    {
      stage: 'Operational Rules', agent: 'Rule Engine',
      status: Array.isArray(planningResponse.rule_results) ? 'COMPLETED' : 'UNKNOWN',
      detail: Array.isArray(planningResponse.rule_results)
        ? `${planningResponse.rule_results.length} flight rule evaluation(s) returned; results may use assumed inputs.`
        : 'No rule results returned.',
    },
    { stage: 'Human Review', agent: 'Operations Team', status: 'AWAITING_ACTION', detail: 'Advisory plan requires human review; no approval action has been executed.' },
  ] : workflow;

  if (!Array.isArray(liveSteps) || !liveSteps.length) {
    return <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center text-xs text-slate-400">No agent workflow results available for this flight.</div>;
  }
  return (
    <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-xl">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <Cpu className="h-5 w-5 text-purple-400" />
        <div>
          <h4 className="text-sm font-bold uppercase tracking-wider text-white">Agent Workflow</h4>
          <p className="text-xs text-slate-400">{planningResponse ? 'Results from the live FastAPI planning request' : 'Workflow data supplied by the parent component (not verified live)'}</p>
        </div>
      </div>
      <div className="space-y-3">
        {liveSteps.map((step, idx) => {
          const done = step.status === 'COMPLETED';
          return <div key={idx} className="flex gap-3 rounded-lg border border-slate-800 bg-slate-950/60 p-3">
            {done ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" /> : <Clock className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-slate-100">{step.stage}</span>
                <span className="text-[10px] text-purple-300">{step.agent}</span>
                <span className="ml-auto text-[10px] font-bold text-slate-400">{String(step.status || 'UNKNOWN').replaceAll('_', ' ')}</span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">{step.detail}</p>
            </div>
          </div>;
        })}
      </div>
    </div>
  );
};
export default AgentWorkflow;
