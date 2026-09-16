import { useEffect, useState } from "react";
import { getMandates } from "../api/mandates";
import { getUpcoming, getHistory } from "../api/payments";
import { getApprovals } from "../api/approvals";
import type { Mandate, Transaction, ApprovalRequest } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function Dashboard() {
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [upcoming, setUpcoming] = useState<Mandate[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [history, setHistory] = useState<Transaction[]>([]);

  useEffect(() => {
    getMandates().then(setMandates).catch(() => {});
    getUpcoming().then(setUpcoming).catch(() => {});
    getApprovals().then(setApprovals).catch(() => {});
    getHistory().then(setHistory).catch(() => {});
  }, []);

  const activeMandates = mandates.filter((m) => m.status === "ACTIVE").length;
  const pausedMandates = mandates.filter((m) => m.status === "PAUSED").length;
  const pendingApprovals = approvals.filter((a) => a.status === "PENDING").length;

  const cards = [
    { label: "Active mandates", value: activeMandates },
    { label: "Paused mandates", value: pausedMandates },
    { label: "Upcoming payments", value: upcoming.length },
    { label: "Pending approvals", value: pendingApprovals },
  ];

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-lg border p-4">
            <div className="text-2xl font-semibold text-slate-800">{c.value}</div>
            <div className="text-sm text-slate-500">{c.label}</div>
          </div>
        ))}
      </div>

      <div>
        <h2 className="font-medium text-slate-800 mb-2">Recent transactions</h2>
        <div className="bg-white rounded-lg border divide-y">
          {history.slice(0, 5).map((t) => (
            <div key={t.id} className="flex justify-between items-center px-4 py-3 text-sm">
              <div>
                <div className="font-medium text-slate-800">{t.merchant_name}</div>
                <div className="text-slate-500">₹{t.amount.toFixed(0)}</div>
              </div>
              <StatusBadge status={t.status} />
            </div>
          ))}
          {history.length === 0 && <div className="px-4 py-6 text-sm text-slate-400">No transactions yet.</div>}
        </div>
      </div>
    </div>
  );
}