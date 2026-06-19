import React from "react";

const COLORS = {
  critical: { ring: "border-red-900/80", text: "text-red-300", accent: "text-red-400" },
  high: { ring: "border-amber-900/80", text: "text-amber-300", accent: "text-amber-400" },
  medium: { ring: "border-blue-900/80", text: "text-blue-300", accent: "text-blue-400" },
  low: { ring: "border-emerald-900/80", text: "text-emerald-300", accent: "text-emerald-400" },
  neutral: { ring: "border-slate-800", text: "text-slate-200", accent: "text-blue-400" },
};

export default function KPICard({ label, value, hint, severity = "neutral", icon: Icon, testid }) {
  const c = COLORS[severity] || COLORS.neutral;
  return (
    <div
      className={`relative bg-[#0A0A0A] border ${c.ring} p-5 rounded-sm overflow-hidden hover:bg-[#0E0E0E] transition-colors duration-150 anim-fade`}
      data-testid={testid}
    >
      <div className="flex items-start justify-between">
        <div className="font-mono text-[10px] tracking-[0.25em] uppercase text-slate-500">{label}</div>
        {Icon ? <Icon size={18} weight="duotone" className={c.accent} /> : null}
      </div>
      <div className={`mt-3 font-mono text-4xl font-bold tracking-tight ${c.text}`}>{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
      <div className={`absolute top-0 left-0 h-full w-[2px] ${c.accent.replace("text", "bg")}`} />
    </div>
  );
}
