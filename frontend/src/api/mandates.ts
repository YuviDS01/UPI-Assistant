import { apiFetch } from "./client";
import type { Mandate } from "../types";

export const getMandates = () => apiFetch<Mandate[]>("/api/mandates");

export const createMandate = (body: {
  merchant_id: string;
  merchant_name: string;
  category: string;
  amount_limit: number;
  frequency: string;
  next_payment_date: string;
}) => apiFetch<Mandate>("/api/mandates", { method: "POST", body: JSON.stringify(body) });

export const cancelMandate = (id: string) =>
  apiFetch<Mandate>(`/api/mandates/${id}/cancel`, { method: "POST" });

export const pauseMandate = (id: string, until: string | null, reason: string | null) =>
  apiFetch<Mandate>(`/api/mandates/${id}/pause`, {
    method: "POST",
    body: JSON.stringify({ until, reason }),
  });

export const resumeMandate = (id: string) =>
  apiFetch<Mandate>(`/api/mandates/${id}/resume`, { method: "POST" });