import { apiFetch } from "./client";
import type { ChatResponse } from "../types";

export const sendMessage = (message: string, threadId: string | null) =>
  apiFetch<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, thread_id: threadId }),
  });