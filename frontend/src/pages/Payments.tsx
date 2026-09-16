import { useEffect, useState } from "react";
import { getHistory, getUpcoming } from "../api/payments";
import type { Mandate, Transaction } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function Payments() {
  const [tab, setTab] = useState<"upcoming" | "history">("upcoming");
  const [upcoming, setUpcoming] = useState<Mandate[]>([]);
  const [history, setHistory] = useState<Transaction[]>([]);

  useEffect(() => {
    getUpcoming().then(setUpcoming).catch(() => {});
    getHistory().then(setHistory).catch(() => {});
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex gap-4 border-b">
        {(["upcoming", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-sm ${tab === t ? "border-b-2 border-indigo-600 text-indigo-600 font-medium" : "text-slate-500"}`}
          >
            {t === "upcoming" ? "Upcoming payments" : "Payment history"}
          </button>
        ))}
      </div>

      {tab === "upcoming" && (
        <div className="bg-white rounded-lg border divide-y">
          {upcoming.map((m) => (
            <div key={m.id} className="flex justify-between items-center px-4 py-3 text-sm">
              <div>
                <div className="font-medium text-slate-800">{m.merchant_name}</div>
                <div className="text-slate-500">Due {m.next_payment_date}</div>
              </div>
              <div className="font-medium">₹{m.amount_limit.toFixed(0)}</div>
            </div>
          ))}
          {upcoming.length === 0 && <div className="px-4 py-6 text-sm text-slate-400">Nothing due soon.</div>}
        </div>
      )}

      {tab === "history" && (
        <div className="bg-white rounded-lg border divide-y">
          {history.map((t) => (
            <div key={t.id} className="flex justify-between items-center px-4 py-3 text-sm">
              <div>
                <div className="font-medium text-slate-800">{t.merchant_name}</div>
                <div className="text-slate-500">
                  ₹{t.amount.toFixed(0)} · {new Date(t.created_at).toLocaleDateString()}
                </div>
              </div>
              <StatusBadge status={t.status} />
            </div>
          ))}
          {history.length === 0 && <div className="px-4 py-6 text-sm text-slate-400">No payments yet.</div>}
        </div>
      )}
    </div>
  );
}