import {
  Activity,
  BrainCircuit,
  ClipboardCheck,
  Database,
  Plane,
  Search,
  Users,
} from "lucide-react";

const agents = [
  {
    name: "Research Agent",
    description: "Collects flight and weather information.",
    status: "Integration Pending",
    icon: Search,
  },
  {
    name: "Analysis Agent",
    description: "Evaluates operational risks and disruptions.",
    status: "Planned",
    icon: Activity,
  },
  {
    name: "Resource Agent",
    description: "Checks gate, runway, and staff availability.",
    status: "Planned",
    icon: Users,
  },
  {
    name: "Planning Agent",
    description: "Generates operational plans using Gemini.",
    status: "Implemented",
    icon: BrainCircuit,
  },
  {
    name: "Decision Agent",
    description: "Supports human review of recommendations.",
    status: "Planned",
    icon: ClipboardCheck,
  },
];

export default function AgentMonitoring() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-sky-400">
          AI Operations
        </p>

        <h1 className="mt-2 text-3xl font-bold text-white">
          AI Agent Monitoring
        </h1>

        <p className="mt-2 text-sm text-slate-400">
          Monitor AI agent development, workflows, and operational
          decision support.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <Database className="mb-3 text-sky-400" size={24} />
          <p className="text-sm text-slate-400">Configured Agents</p>
          <h2 className="mt-2 text-3xl font-bold">5</h2>
          <p className="mt-1 text-xs text-slate-500">
            Including planned agents
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <BrainCircuit className="mb-3 text-green-400" size={24} />
          <p className="text-sm text-slate-400">Implemented Agents</p>
          <h2 className="mt-2 text-3xl font-bold">1</h2>
          <p className="mt-1 text-xs text-slate-500">
            Gemini Planning Agent
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <Plane className="mb-3 text-amber-400" size={24} />
          <p className="text-sm text-slate-400">Gate Availability</p>
          <h2 className="mt-2 text-xl font-bold">Integrated</h2>
          <p className="mt-1 text-xs text-slate-500">
            Shared backend tool
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-5">
          <h2 className="text-xl font-semibold">
            Agent Workflow
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Current implementation and planned capabilities.
          </p>
        </div>

        <div className="space-y-3">
          {agents.map((agent) => {
            const Icon = agent.icon;

            return (
              <div
                key={agent.name}
                className="flex items-center justify-between gap-4 rounded-lg border border-slate-800 bg-slate-950 p-4"
              >
                <div className="flex items-center gap-4">
                  <div className="rounded-lg bg-sky-500/10 p-3">
                    <Icon className="text-sky-400" size={22} />
                  </div>

                  <div>
                    <h3 className="font-semibold text-white">
                      {agent.name}
                    </h3>

                    <p className="mt-1 text-sm text-slate-400">
                      {agent.description}
                    </p>
                  </div>
                </div>

                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    agent.status === "Implemented"
                      ? "bg-green-500/10 text-green-400"
                      : "bg-amber-500/10 text-amber-400"
                  }`}
                >
                  {agent.status}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="text-lg font-semibold">
          Integration Status
        </h2>

        <p className="mt-2 text-sm text-slate-400">
          The Planning Agent and Gate Availability Tool are implemented.
          Flight Research, live agent activity, and Decision Support
          API integration will be added in the next steps.
        </p>
      </div>
    </div>
  );
}