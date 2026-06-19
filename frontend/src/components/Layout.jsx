import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  ShieldCheck, Gauge, FileText, BellRinging, MagnifyingGlass,
  FileArrowDown, GridFour, Gear, SignOut, Terminal,
} from "@phosphor-icons/react";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: Gauge, testid: "nav-dashboard" },
  { to: "/logs", label: "Logs", icon: FileText, testid: "nav-logs" },
  { to: "/alerts", label: "Alerts", icon: BellRinging, testid: "nav-alerts" },
  { to: "/investigation", label: "Investigation", icon: MagnifyingGlass, testid: "nav-investigation" },
  { to: "/reports", label: "Reports", icon: FileArrowDown, testid: "nav-reports" },
  { to: "/mitre", label: "MITRE ATT&CK", icon: GridFour, testid: "nav-mitre" },
  { to: "/settings", label: "Settings", icon: Gear, testid: "nav-settings" },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-[#050505] text-slate-100">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 border-r border-slate-800 bg-[#070708] flex flex-col" data-testid="sidebar">
        <div className="px-5 py-5 border-b border-slate-800 flex items-center gap-2">
          <ShieldCheck size={22} weight="duotone" className="text-blue-500" />
          <div>
            <div className="font-mono font-bold tracking-tight text-sm">SOC<span className="text-blue-500">.</span>ANALYZER</div>
            <div className="font-mono text-[9px] tracking-[0.25em] text-slate-500 uppercase">Security Console</div>
          </div>
        </div>
        <nav className="flex-1 px-2 py-4 space-y-0.5">
          {NAV.map(({ to, label, icon: Icon, testid }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-all duration-150 font-medium ${
                  isActive
                    ? "bg-blue-500/10 text-blue-300 border-l-2 border-blue-500 pl-[10px]"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-900/60"
                }`
              }
            >
              <Icon size={16} weight="duotone" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 p-3 space-y-2">
          <div className="px-2 py-1.5">
            <div className="font-mono text-[9px] tracking-[0.25em] text-slate-500 uppercase">Analyst</div>
            <div className="text-xs text-slate-200 truncate" data-testid="sidebar-user-name">{user?.name}</div>
            <div className="text-[10px] text-slate-500 truncate font-mono">{user?.email}</div>
          </div>
          <button
            onClick={handleLogout}
            data-testid="logout-btn"
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-300 hover:bg-red-500/10 hover:text-red-300 rounded-sm transition-all duration-150 font-mono uppercase tracking-wider"
          >
            <SignOut size={14} weight="bold" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b border-slate-800 bg-[#070708] px-6 py-3 flex items-center justify-between" data-testid="top-bar">
          <div className="flex items-center gap-3">
            <Terminal size={16} weight="bold" className="text-emerald-500" />
            <span className="font-mono text-[10px] tracking-[0.25em] uppercase text-slate-400">
              Live <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 pulse-dot align-middle ml-1" />
            </span>
          </div>
          <div className="font-mono text-[10px] tracking-widest text-slate-500 uppercase">
            {new Date().toISOString().replace("T", " · ").slice(0, 19)} UTC
          </div>
        </header>
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </main>
    </div>
  );
}
