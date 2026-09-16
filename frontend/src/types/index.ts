export interface Mandate {
  id: string;
  merchant_id: string;
  merchant_name: string;
  category: string;
  amount_limit: number;
  frequency: string;
  next_payment_date: string;
  status: "ACTIVE" | "PAUSED" | "CANCELLED" | "EXPIRED";
  pause_reason: string | null;
  paused_until: string | null;
  provider_mandate_id: string | null;
  created_at: string;
}

export interface Transaction {
  id: string;
  mandate_id: string | null;
  merchant_id: string;
  merchant_name: string;
  category: string;
  amount: number;
  currency: string;
  payment_type: "RECURRING" | "NEW";
  status: "PENDING" | "PROCESSING" | "SUCCESS" | "FAILED" | "CANCELLED";
  provider_transaction_id: string | null;
  failure_reason: string | null;
  created_at: string;
}

export interface ApprovalRequest {
  id: string;
  transaction_id: string;
  reason: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";
  expires_at: string;
  approved_at: string | null;
  rejected_at: string | null;
  created_at: string;
}

export interface ChatResponse {
  thread_id: string;
  intent: string;
  response: string;
  requires_approval: boolean;
  tool_result: Record<string, unknown> | null;
}