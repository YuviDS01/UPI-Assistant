import { useEffect, useState } from "react";
import { approveApproval, getApprovals, rejectApproval } from "../api/approvals";
import type { ApprovalRequest } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function Approvals() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);

  function refresh() {
    getApprovals().then(setApprovals).catch(() => {});
  }

  useEffect(refresh, []);

  async function handleApprove(id: string) {
    await approveApproval(id);
    refresh();
  }

  async function handleReject(id: string) {
    await rejectApproval(id);
    refresh();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Approval requests</h1>
      <div className="bg-white rounded-lg border divide-y">
        {approvals.map((a) => (
          <div key={a.id} className="p-4 space-y-2">
            <div className="flex justify-between items-start">
              <div>
                <div className="text-sm text-slate-500">{a.reason}</div>
                <div className="text-xs text-slate-400">Expires {new Date(a.expires_at).toLocaleString()}</div>
              </div>
              <StatusBadge status={a.status} />
            </div>
            {a.status === "PENDING" && (
              <div className="flex gap-2">
                <button
                  onClick={() => handleApprove(a.id)}
                  className="text-sm px-3 py-1 rounded-md bg-green-600 text-white"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleReject(a.id)}
                  className="text-sm px-3 py-1 rounded-md border border-red-300 text-red-700"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        ))}
        {approvals.length === 0 && <div className="p-6 text-sm text-slate-400">No approval requests.</div>}
      </div>
    </div>
  );
}