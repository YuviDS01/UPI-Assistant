import { useState } from "react";
import { sendMessage } from "../api/chat";
import { ApiError } from "../api/client";

interface Message {
  role: "user" | "assistant";
  text: string;
}

const THREAD_STORAGE_KEY = "upi_chat_thread_id";

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(
    localStorage.getItem(THREAD_STORAGE_KEY)
  );

  async function handleSend() {
    if (!input.trim()) return;
    const userText = input;
    setMessages((prev) => [...prev, { role: "user", text: userText }]);
    setInput("");
    setLoading(true);

    try {
      const result = await sendMessage(userText, threadId);
      setThreadId(result.thread_id);
      localStorage.setItem(THREAD_STORAGE_KEY, result.thread_id);
      setMessages((prev) => [...prev, { role: "assistant", text: result.response }]);
    } catch (err) {
      // Surface the REAL error instead of a generic message, so this
      // never hides a CORS/network/auth problem behind unhelpful text again.
      const text =
        err instanceof ApiError
          ? `Error (${err.errorCode}): ${err.message}`
          : `Couldn't reach the backend at all — check it's running and CORS is configured (${err instanceof Error ? err.message : "unknown error"}).`;
      setMessages((prev) => [...prev, { role: "assistant", text }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[70vh] bg-white rounded-lg border">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-sm text-slate-400">
            Try: "Automatically pay my electricity bill every month up to ₹2,500." or "Pause my Netflix
            payment for 2 months."
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[75%] rounded-lg px-3 py-2 text-sm whitespace-pre-line ${
                m.role === "user" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-800"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && <div className="text-sm text-slate-400">Thinking…</div>}
      </div>
      <div className="border-t p-3 flex gap-2">
        <input
          className="flex-1 border rounded-md px-3 py-2 text-sm"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Message the assistant…"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="bg-indigo-600 text-white text-sm px-4 py-2 rounded-md disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}