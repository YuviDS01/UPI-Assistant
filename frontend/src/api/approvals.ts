import { apiFetch } from "./client";
import type { ApprovalRequest } from "../types";

export const getApprovals = () => apiFetch<ApprovalRequest[]>("/api/approvals");

export const approveApproval = (id: string) =>
  apiFetch<{ approval: ApprovalRequest; execution_result: Record<string, unknown> }>(
    `/api/approvals/${id}/approve`,
    { method: "POST" }
  );

export const rejectApproval = (id: string) =>
  apiFetch<{ approval: ApprovalRequest }>(`/api/approvals/${id}/reject`, { method: "POST" });