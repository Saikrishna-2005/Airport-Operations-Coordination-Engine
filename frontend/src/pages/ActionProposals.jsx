import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  ClipboardCheck,
  RefreshCw,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  AlertCircle,
  LoaderCircle,
  Plane,
} from "lucide-react";

import {
  getActionProposals,
  generateActionProposals,
  reviewActionProposal,
} from "../services/actionProposalApi";


// ============================================================
// STATUS BADGE
// ============================================================

function StatusBadge({ value }) {
  const styles = {
    pending: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    validated: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    approved: "bg-green-500/10 text-green-300 border-green-500/30",
    rejected: "bg-red-500/10 text-red-300 border-red-500/30",
    failed: "bg-red-500/10 text-red-300 border-red-500/30",
    not_started: "bg-slate-700 text-slate-300 border-slate-600",
  };

  const normalized = String(value || "unknown").toLowerCase();

  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${
        styles[normalized] ||
        "border-slate-700 bg-slate-800 text-slate-300"
      }`}
    >
      {normalized.replace(/_/g, " ").toUpperCase()}
    </span>
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
    </div>
  );
}


// ============================================================
// PARSE PAYLOAD
// ============================================================

function parsePayload(payload) {
  if (!payload) return {};

  if (typeof payload === "object") {
    return payload;
  }

  try {
    return JSON.parse(payload);
  } catch {
    return {};
  }
}


// ============================================================
// MAIN COMPONENT
// ============================================================

export default function ActionProposals({ userRole }) {
  const isAdmin = userRole === "admin";

  // URL WORKFLOW FILTER
  const [searchParams, setSearchParams] = useSearchParams();

  const workflowIdFromUrl =
    searchParams.get("workflow_id")?.trim() || "";

  // STATES
  const [proposals, setProposals] = useState([]);

  const [workflowId, setWorkflowId] = useState(
    workflowIdFromUrl
  );

  const [loading, setLoading] = useState(true);

  const [generating, setGenerating] = useState(false);

  const [reviewingId, setReviewingId] = useState(null);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");

  const [reviewComments, setReviewComments] = useState({});


  // ==========================================================
  // SYNC WORKFLOW ID WITH URL
  // ==========================================================

  useEffect(() => {
    setWorkflowId(workflowIdFromUrl);
  }, [workflowIdFromUrl]);


  // ==========================================================
  // FILTER PROPOSALS BY WORKFLOW ID
  // ==========================================================

  const displayedProposals = workflowIdFromUrl
    ? proposals.filter(
        (proposal) =>
          proposal.workflow_id === workflowIdFromUrl
      )
    : proposals;


  // ==========================================================
  // LOAD PROPOSALS
  // ==========================================================

  async function loadProposals() {
    setLoading(true);
    setError("");

    try {
      const data = await getActionProposals();

      setProposals(
        Array.isArray(data) ? data : []
      );
    } catch (err) {
      console.error("Failed to load action proposals:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to retrieve action proposals."
      );
    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    loadProposals();
  }, []);


  // ==========================================================
  // GENERATE ACTION PROPOSALS
  // ==========================================================

  async function handleGenerate(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    const requestedWorkflowId = workflowId.trim();

    if (!requestedWorkflowId) {
      setError("Please enter a workflow ID.");
      return;
    }

    setGenerating(true);

    try {
      const result = await generateActionProposals(
        requestedWorkflowId
      );

      setSuccess(
        `${result.generated_count} action proposal(s) generated successfully.`
      );

      // Navigate/filter using the generated workflow ID.
      setSearchParams({
        workflow_id: requestedWorkflowId,
      });

      setWorkflowId("");

      await loadProposals();
    } catch (err) {
      console.error("Proposal generation failed:", err);

      setError(
        err.response?.data?.detail ||
          "Action proposal generation failed."
      );
    } finally {
      setGenerating(false);
    }
  }


  // ==========================================================
  // ADMIN REVIEW
  // ==========================================================

  async function handleReview(actionId, decision) {
    const comment = reviewComments[actionId] || "";

    if (comment.trim().length < 3) {
      setError(
        "Please enter a review comment containing at least 3 characters."
      );
      return;
    }

    setError("");
    setSuccess("");

    setReviewingId(actionId);

    try {
      await reviewActionProposal(
        actionId,
        decision,
        comment
      );

      setSuccess(
        `Action proposal ${decision} successfully.`
      );

      setReviewComments((previous) => ({
        ...previous,
        [actionId]: "",
      }));

      await loadProposals();
    } catch (err) {
      console.error("Action review failed:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to review action proposal."
      );
    } finally {
      setReviewingId(null);
    }
  }


  // ==========================================================
  // SUMMARY COUNTS
  // ==========================================================

  const total = displayedProposals.length;

  const pending = displayedProposals.filter(
    (item) => item.approval_status === "pending"
  ).length;

  const approved = displayedProposals.filter(
    (item) => item.approval_status === "approved"
  ).length;

  const rejected = displayedProposals.filter(
    (item) => item.approval_status === "rejected"
  ).length;

  const failed = displayedProposals.filter(
    (item) => item.validation_status === "failed"
  ).length;


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="space-y-6 text-white">

      {/* HEADER */}

      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-sky-400/10 p-3">
            <ClipboardCheck
              size={28}
              className="text-sky-400"
            />
          </div>

          <div>
            <h1 className="text-2xl font-bold">
              AI Action Proposals
            </h1>

            <p className="mt-1 text-sm text-slate-400">
              Evidence-based operational proposals and human approval.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadProposals}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={loading ? "animate-spin" : ""}
          />
          Refresh
        </button>
      </header>


      {/* MESSAGES */}

      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
        >
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {success && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300"
        >
          <CheckCircle2 size={18} />
          {success}
        </div>
      )}


      {/* WORKFLOW FILTER INDICATOR */}

      {workflowIdFromUrl && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
          <div>
            <p className="text-sm font-semibold text-blue-300">
              Workflow Filter Active
            </p>

            <p className="mt-1 break-all text-xs text-blue-200">
              Showing proposals for workflow:{" "}
              <span className="font-semibold">
                {workflowIdFromUrl}
              </span>
            </p>
          </div>

          <button
            type="button"
            onClick={() => setSearchParams({})}
            className="rounded-lg border border-blue-400/30 px-3 py-2 text-sm font-medium text-blue-300 hover:bg-blue-400/10"
          >
            Clear Filter
          </button>
        </div>
      )}


      {/* SUMMARY CARDS */}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">

        <SummaryCard
          title="Total Proposals"
          value={total}
          icon={ClipboardCheck}
          color="text-sky-400"
        />

        <SummaryCard
          title="Pending Approval"
          value={pending}
          icon={Clock}
          color="text-amber-400"
        />

        <SummaryCard
          title="Approved"
          value={approved}
          icon={CheckCircle2}
          color="text-emerald-400"
        />

        <SummaryCard
          title="Rejected"
          value={rejected}
          icon={XCircle}
          color="text-red-400"
        />

        <SummaryCard
          title="Validation Failed"
          value={failed}
          icon={ShieldCheck}
          color="text-orange-400"
        />

      </section>


      {/* GENERATE PROPOSALS */}

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">

        <div className="mb-4 flex items-center gap-2">
          <Play size={20} className="text-sky-400" />

          <h2 className="font-semibold">
            Generate Action Proposals
          </h2>
        </div>

        <p className="mb-4 text-sm leading-6 text-slate-400">
          Enter an existing workflow ID. The Action Proposal Generator
          will examine its planning results, research findings and
          operational rule results.
        </p>

        <form
          onSubmit={handleGenerate}
          className="flex flex-col gap-3 sm:flex-row"
        >
          <input
            value={workflowId}
            onChange={(event) =>
              setWorkflowId(event.target.value)
            }
            placeholder="Enter workflow ID"
            className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-sky-400"
            required
          />

          <button
            type="submit"
            disabled={generating}
            className="flex items-center justify-center gap-2 rounded-lg bg-sky-400 px-6 py-3 font-semibold text-slate-950 hover:bg-sky-300 disabled:opacity-50"
          >
            {generating ? (
              <>
                <LoaderCircle
                  size={18}
                  className="animate-spin"
                />
                Generating...
              </>
            ) : (
              <>
                <Play size={18} />
                Generate Proposals
              </>
            )}
          </button>
        </form>

      </section>


      {/* PROPOSAL LIST */}

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">

        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            Generated Proposals
          </h2>

          <span className="text-xs text-slate-500">
            {total} records
          </span>
        </div>


        {loading ? (

          <div className="flex items-center justify-center gap-3 py-12 text-slate-400">
            <LoaderCircle
              size={22}
              className="animate-spin"
            />
            Loading proposals...
          </div>

        ) : displayedProposals.length === 0 ? (

          <div className="py-12 text-center">
            <ClipboardCheck
              size={36}
              className="mx-auto mb-3 text-slate-600"
            />

            <p className="font-medium text-slate-300">
              No action proposals found.
            </p>

            <p className="mt-2 text-sm text-slate-500">
              {workflowIdFromUrl
                ? "No proposals are associated with this workflow ID."
                : "Generate proposals using an existing workflow ID."}
            </p>
          </div>

        ) : (

          <div className="space-y-5">

            {displayedProposals.map((proposal) => {

              const payload = parsePayload(proposal.payload);

              const canReview =
                isAdmin &&
                proposal.validation_status === "validated" &&
                proposal.approval_status === "pending";

              return (

                <article
                  key={proposal.action_id}
                  className="rounded-xl border border-slate-800 bg-slate-950 p-5"
                >

                  {/* PROPOSAL HEADER */}

                  <div className="flex flex-wrap items-start justify-between gap-4">

                    <div>
                      <div className="flex items-center gap-2">
                        <Plane
                          size={18}
                          className="text-sky-400"
                        />

                        <h3 className="font-semibold text-white">
                          {proposal.target_flight || "General Operation"}
                        </h3>
                      </div>

                      <p className="mt-2 text-xs text-slate-500">
                        {proposal.action_id}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <StatusBadge
                        value={proposal.validation_status}
                      />

                      <StatusBadge
                        value={proposal.approval_status}
                      />
                    </div>

                  </div>


                  {/* ACTION DETAILS */}

                  <div className="mt-5 space-y-3">

                    <div>
                      <p className="text-xs text-slate-500">
                        Action Type
                      </p>

                      <p className="mt-1 font-semibold text-sky-300">
                        {proposal.action_type?.replace(/_/g, " ")}
                      </p>
                    </div>


                    <div>
                      <p className="text-xs text-slate-500">
                        Description
                      </p>

                      <p className="mt-1 text-sm leading-6 text-slate-300">
                        {proposal.description}
                      </p>
                    </div>


                    <div className="grid gap-3 sm:grid-cols-2">

                      <div className="rounded-lg bg-slate-900 p-3">
                        <p className="text-xs text-slate-500">
                          Airport
                        </p>

                        <p className="mt-1 font-semibold">
                          {proposal.airport}
                        </p>
                      </div>

                      <div className="rounded-lg bg-slate-900 p-3">
                        <p className="text-xs text-slate-500">
                          Execution Status
                        </p>

                        <div className="mt-2">
                          <StatusBadge
                            value={proposal.execution_status}
                          />
                        </div>
                      </div>

                    </div>


                    {/* PAYLOAD */}

                    <details className="rounded-lg border border-slate-800 p-3">

                      <summary className="cursor-pointer text-sm font-medium text-sky-300">
                        View Action Payload
                      </summary>

                      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-6 text-slate-400">
                        {JSON.stringify(payload, null, 2)}
                      </pre>

                    </details>


                    {/* ADMIN APPROVAL */}

                    {canReview && (

                      <div className="border-t border-slate-800 pt-4">

                        <h4 className="mb-3 flex items-center gap-2 font-semibold text-white">
                          <ShieldCheck
                            size={18}
                            className="text-emerald-400"
                          />
                          Administrator Review
                        </h4>

                        <textarea
                          value={reviewComments[proposal.action_id] || ""}
                          onChange={(event) =>
                            setReviewComments((previous) => ({
                              ...previous,
                              [proposal.action_id]: event.target.value,
                            }))
                          }
                          placeholder="Enter your review comment..."
                          rows={2}
                          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-3 text-sm outline-none focus:border-sky-400"
                        />

                        <div className="mt-3 flex flex-wrap gap-3">

                          <button
                            type="button"
                            onClick={() =>
                              handleReview(proposal.action_id, "approved")
                            }
                            disabled={reviewingId === proposal.action_id}
                            className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-400 disabled:opacity-50"
                          >
                            <CheckCircle2 size={16} />
                            Approve
                          </button>

                          <button
                            type="button"
                            onClick={() =>
                              handleReview(proposal.action_id, "rejected")
                            }
                            disabled={reviewingId === proposal.action_id}
                            className="flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white hover:bg-red-400 disabled:opacity-50"
                          >
                            <XCircle size={16} />
                            Reject
                          </button>

                        </div>

                      </div>

                    )}


                    {!canReview &&
                      proposal.validation_status === "failed" && (

                        <p className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
                          This proposal failed safety validation and
                          cannot be approved.
                        </p>

                      )}


                    {!canReview &&
                      !isAdmin &&
                      proposal.approval_status === "pending" && (

                        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
                          Administrator approval is required.
                        </p>

                      )}

                  </div>

                </article>

              );
            })}

          </div>

        )}

      </section>


      {/* SAFETY NOTICE */}

      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">

        <div className="flex items-start gap-3">

          <AlertCircle
            size={20}
            className="mt-0.5 shrink-0 text-amber-400"
          />

          <div>
            <h3 className="font-semibold text-amber-300">
              Operational Safety Notice
            </h3>

            <p className="mt-2 text-sm leading-6 text-amber-200/80">
              AI-generated proposals are advisory. Validation and
              administrator approval do not execute airport operations
              or grant runway, gate or flight clearances. Execution
              requires a separately authorized and controlled process.
            </p>
          </div>

        </div>

      </div>

    </div>
  );
}