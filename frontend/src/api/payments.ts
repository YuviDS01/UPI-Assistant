import { apiFetch } from "./client";
import type { Mandate, Transaction } from "../types";

export const getHistory = () => apiFetch<Transaction[]>("/api/payments?limit=50");
export const getUpcoming = () => apiFetch<Mandate[]>("/api/payments/upcoming");
export const getPayment = (id: string) => apiFetch<Transaction>(`/api/payments/${id}`);

export const simulatePayment = (body: {
  merchant_id: string;
  merchant_name: string;
  category: string;
  amount: number;
}) =>
  apiFetch<{ transaction: Transaction; execution_result: Record<string, unknown>; approval_id: string | null }>(
    "/api/payments/simulate",
    { method: "POST", body: JSON.stringify(body) }
  );