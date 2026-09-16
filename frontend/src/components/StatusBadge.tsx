const COLORS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  PAUSED: "bg-amber-100 text-amber-800",
  CANCELLED: "bg-gray-200 text-gray-600",
  EXPIRED: "bg-gray-200 text-gray-600",
  SUCCESS: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
  PENDING: "bg-blue-100 text-blue-800",
  PROCESSING: "bg-blue-100 text-blue-800",
  APPROVED: "bg-green-100 text-green-800",
  REJECTED: "bg-gray-200 text-gray-600",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${COLORS[status] || "bg-gray-100 text-gray-700"}`}>
      {status}
    </span>
  );
}