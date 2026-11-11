import api from "../api";

// Retrieve all action proposals
export const getActionProposals = async () => {
  const response = await api.get("/actions/proposals");

  return response.data;
};


// Generate proposals from an existing workflow
export const generateActionProposals = async (workflowId) => {
  if (!workflowId || !workflowId.trim()) {
    throw new Error("Workflow ID is required.");
  }

  const response = await api.post(
    `/actions/proposals/generate/${encodeURIComponent(workflowId.trim())}`
  );

  return response.data;
};


// Approve or reject an action proposal
export const reviewActionProposal = async (
  actionId,
  decision,
  reviewComment
) => {
  if (!actionId) {
    throw new Error("Action ID is required.");
  }

  if (!["approved", "rejected"].includes(decision)) {
    throw new Error("Invalid review decision.");
  }

  if (!reviewComment || reviewComment.trim().length < 3) {
    throw new Error("Review comment must contain at least 3 characters.");
  }

  const response = await api.patch(
    `/actions/proposals/${encodeURIComponent(actionId)}/review`,
    {
      decision,
      review_comment: reviewComment.trim(),
    }
  );

  return response.data;
};