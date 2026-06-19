import React from "react";
import { ShieldCheck } from "@phosphor-icons/react";

export default function AuthShell({ title, subtitle, children, testid }) {
  return (
    <div className="min-h-screen flex bg-[#050505] text-slate-100" data-testid={testid}>
      {/* Left panel with decorative imagery */}
      <div className="hidden md:flex md:w-1/2 relative overflow-hidden border-r border-slate-800">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "url('https://images.unsplash.com/photo-1687603858673-a08a2dc2302c')" }}
        />
        <div className="absolute inset-0 bg-black/80" />
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div className="relative z-10 p-12 flex flex-col justify-between w-full">
          <div className="flex items-center gap-2">
            <ShieldCheck size={28} weight="duotone" className="text-blue-500" />
            <div>
              <div className="font-mono font-bold text-base tracking-tight">SOC<span className="text-blue-500">.</span>ANALYZER</div>
              <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-slate-500">Security Console v1.0</div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-emerald-400 flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full pulse-dot" />
              Threat engine online
            </div>
            <h1 className="font-mono text-4xl font-bold tracking-tight leading-tight">
              Detect. Investigate.
              <span className="text-blue-500">.</span>
              <br/>Respond.
            </h1>
            <p className="text-sm text-slate-400 max-w-md">
              Real-time analysis of authentication logs to surface brute-force attacks,
              suspicious IPs and unusual access patterns.
            </p>
            <div className="grid grid-cols-3 gap-3 pt-4 border-t border-slate-800/80">
              {[
                { v: "12.4M", l: "Events / day" },
                { v: "<150ms", l: "Detection" },
                { v: "MITRE", l: "ATT&CK" },
              ].map((s) => (
                <div key={s.l}>
                  <div className="font-mono text-lg font-bold text-slate-100">{s.v}</div>
                  <div className="font-mono text-[9px] tracking-widest uppercase text-slate-500">{s.l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right panel: form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="md:hidden mb-8 flex items-center gap-2">
            <ShieldCheck size={24} weight="duotone" className="text-blue-500" />
            <div className="font-mono font-bold tracking-tight">SOC<span className="text-blue-500">.</span>ANALYZER</div>
          </div>
          <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-blue-500 mb-2">{subtitle}</div>
          <h2 className="font-mono text-3xl font-bold tracking-tight mb-8">{title}</h2>
          {children}
        </div>
      </div>
    </div>
  );
}
