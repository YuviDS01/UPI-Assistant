import { useEffect, useState } from "react";
import { cancelMandate, getMandates, pauseMandate, resumeMandate } from "../api/mandates";
import type { Mandate } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function Mandates() {
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [pausingId, setPausingId] = useState<string | null>(null);
  const [pauseUntil, setPauseUntil] = useState("");
  const [pauseReason, setPauseReason] = useState("");

  function refresh() {
    getMandates().then(setMandates).catch(() => {});
  }

  useEffect(refresh, []);

  async function handlePauseSubmit(id: string) {
    await pauseMandate(id, pauseUntil || null, pauseReason || null);
    setPausingId(null);
    setPauseUntil("");
    setPauseReason("");
    refresh();
  }

  async function handleResume(id: string) {
    await resumeMandate(id);
    refresh();
  }

  async function handleCancel(id: string) {
    if (!confirm("This permanently cancels the mandate — you'd need to set it up again later. Continue?")) return;
    await cancelMandate(id);
    refresh();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Mandates</h1>
      <div className="bg-white rounded-lg border divide-y">
        {mandates.map((m) => (
          <div key={m.id} className="p-4 space-y-2">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-medium text-slate-800">{m.merchant_name}</div>
                <div className="text-sm text-slate-500">
                  ₹{m.amount_limit.toFixed(0)} · {m.frequency.toLowerCase()} · next: {m.next_payment_date}
                </div>
                {m.status === "PAUSED" && (
                  <div className="text-xs text-amber-700 mt-1">
                    Paused{m.paused_until ? ` until ${m.paused_until}` : " indefinitely"}
                    {m.pause_reason ? ` — ${m.pause_reason}` : ""}
                  </div>
                )}
              </div>
              <StatusBadge status={m.status} />
            </div>

            {m.status === "ACTIVE" && (
              <div className="flex gap-2">
                <button
                  onClick={() => setPausingId(m.id)}
                  className="text-sm px-3 py-1 rounded-md border border-amber-300 text-amber-700 hover:bg-amber-50"
                >
                  Pause
                </button>
                <button
                  onClick={() => handleCancel(m.id)}
                  className="text-sm px-3 py-1 rounded-md border border-red-300 text-red-700 hover:bg-red-50"
                >
                  Cancel
                </button>
              </div>
            )}
            {m.status === "PAUSED" && (
              <button
                onClick={() => handleResume(m.id)}
                className="text-sm px-3 py-1 rounded-md border border-green-300 text-green-700 hover:bg-green-50"
              >
                Resume — no re-authorization needed
              </button>
            )}

            {pausingId === m.id && (
              <div className="mt-2 border rounded-md p-3 bg-slate-50 space-y-2">
                <div className="text-xs text-slate-500">
                  Leave "until" blank to pause indefinitely until you resume it.
                </div>
                <input
                  type="date"
                  value={pauseUntil}
                  onChange={(e) => setPauseUntil(e.target.value)}
                  className="border rounded px-2 py-1 text-sm"
                />
                <input
                  type="text"
                  placeholder="Reason (optional)"
                  value={pauseReason}
                  onChange={(e) => setPauseReason(e.target.value)}
                  className="border rounded px-2 py-1 text-sm w-full"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handlePauseSubmit(m.id)}
                    className="text-sm px-3 py-1 rounded-md bg-amber-600 text-white"
                  >
                    Confirm pause
                  </button>
                  <button onClick={() => setPausingId(null)} className="text-sm px-3 py-1 text-slate-500">
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {mandates.length === 0 && <div className="p-6 text-sm text-slate-400">No mandates yet — create one from the Chat tab.</div>}
      </div>
    </div>
  );
}