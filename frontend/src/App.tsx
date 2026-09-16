import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import Mandates from "./pages/Mandates";
import Payments from "./pages/Payments";
import Approvals from "./pages/Approvals";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/chat", label: "Chat" },
  { to: "/mandates", label: "Mandates" },
  { to: "/payments", label: "Payments" },
  { to: "/approvals", label: "Approvals" },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <nav className="bg-white border-b px-6 py-3 flex gap-6 items-center">
        <span className="font-semibold text-slate-800">UPI Payment Assistant</span>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `text-sm ${isActive ? "text-indigo-600 font-medium" : "text-slate-500 hover:text-slate-800"}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="max-w-4xl mx-auto p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/mandates" element={<Mandates />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/approvals" element={<Approvals />} />
        </Routes>
      </main>
    </div>
  );
}