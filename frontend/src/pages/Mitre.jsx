import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";

export default function Mitre() {
  const [tactics, setTactics] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/mitre/matrix");
        setTactics(data.tactics || []);
      } catch (err) { toast.error(apiError(err)); }
    })();
  }, []);

  return (
    <div className="space-y-5 anim-fade" data-testid="mitre-page">
      <div>
        <div className="section-label">// Adversary Tactics</div>
        <h1 className="font-mono text-3xl font-bold tracking-tight">MITRE ATT&CK Matrix</h1>
        <p className="text-xs text-slate-400 mt-2 max-w-2xl">
          Detected alerts mapped to MITRE ATT&CK techniques. Cell intensity scales with hit count.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {tactics.map((tac) => (
          <div key={tac.id} className="card p-3 flex flex-col" data-testid={`tactic-${tac.id}`}>
            <div className="font-mono text-[9px] tracking-widest uppercase text-blue-400">{tac.id}</div>
            <div className="font-mono text-xs font-bold mb-2 text-slate-100">{tac.name}</div>
            <div className="space-y-1 flex-1">
              {tac.techniques.map((t) => {
                const intensity = Math.min(1, t.hits / 10);
                const bg = t.hits > 0
                  ? `rgba(239,68,68,${0.15 + intensity * 0.5})`
                  : "transparent";
                return (
                  <div key={t.id} className="px-2 py-1.5 border border-slate-800 rounded-sm"
                    style={{ background: bg }}>
                    <div className="font-mono text-[9px] text-slate-500 tracking-widest">{t.id}</div>
                    <div className="text-[11px] text-slate-200">{t.name}</div>
                    {t.hits > 0 && <div className="font-mono text-[9px] text-red-300 mt-0.5">{t.hits} hit{t.hits>1?"s":""}</div>}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
