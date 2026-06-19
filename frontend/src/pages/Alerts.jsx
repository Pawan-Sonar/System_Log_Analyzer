import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCircle, BellSlash } from "@phosphor-icons/react";
import { api, apiError } from "../lib/api";
import SeverityBadge from "../components/SeverityBadge";

const SEV_OPTS = ["", "critical", "high", "medium", "low"];

export default function Alerts() {
  const [items, setItems] = useState([]);
  const [severity, setSeverity] = useState("");

  const load = async () => {
    try {
      const { data } = await api.get("/alerts", { params: severity ? { severity } : {} });
      setItems(data.items || []);
    } catch (err) { toast.error(apiError(err)); }
  };

  useEffect(() => { load(); }, [severity]);

  const ack = async (id) => {
    try {
      await api.post(`/alerts/${id}/acknowledge`);
      toast.success("Acknowledged.");
      load();
    } catch (err) { toast.error(apiError(err)); }
  };

  const downloadCsv = async () => {
    try {
      const res = await api.get("/reports/csv/alerts", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = "alerts.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { toast.error(apiError(err)); }
  };

  return (
    <div className="space-y-5 anim-fade" data-testid="alerts-page">
      <div className="flex items-end justify-between gap-3 flex-wrap">
        <div>
          <div className="section-label">// Incident Stream</div>
          <h1 className="font-mono text-3xl font-bold tracking-tight">Security Alerts</h1>
        </div>
        <div className="flex gap-2 items-end">
          <label className="block">
            <span className="font-mono text-[9px] tracking-[0.25em] uppercase text-slate-500 mb-1 block">Severity</span>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)} data-testid="alert-severity-filter"
              className="input text-xs h-[34px]">
              {SEV_OPTS.map((o) => <option key={o} value={o}>{o || "All"}</option>)}
            </select>
          </label>
          <button onClick={downloadCsv} data-testid="alerts-export-csv"
            className="px-4 py-2 text-xs font-mono uppercase tracking-widest border border-slate-800 hover:border-blue-500 hover:text-blue-300 text-slate-300 rounded-sm">
            Export CSV
          </button>
        </div>
      </div>

      <div className="space-y-2" data-testid="alerts-list">
        {items.length === 0 && (
          <div className="card p-12 flex flex-col items-center justify-center text-center gap-3">
            <BellSlash size={28} weight="duotone" className="text-slate-700" />
            <div className="font-mono text-xs uppercase tracking-widest text-slate-500">No alerts to display</div>
          </div>
        )}
        {items.map((a) => (
          <div key={a.id} className={`card p-4 anim-fade ${a.acknowledged ? "opacity-60" : ""}`} data-testid={`alert-${a.id}`}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <SeverityBadge severity={a.severity} />
                  <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest">{a.type}</span>
                  {a.mitre_id && (
                    <span className="font-mono text-[10px] text-blue-400 border border-blue-900/50 px-1.5 py-0.5">
                      {a.mitre_id}
                    </span>
                  )}
                </div>
                <div className="text-sm text-slate-200">{a.message}</div>
                <div className="mt-2 flex items-center gap-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                  <span>{(a.timestamp || "").replace("T", " ").slice(0, 19)}</span>
                  {a.ip_address && <span>IP: <span className="text-slate-300">{a.ip_address}</span></span>}
                  {a.username && <span>User: <span className="text-slate-300">{a.username}</span></span>}
                </div>
              </div>
              {!a.acknowledged && (
                <button onClick={() => ack(a.id)} data-testid={`alert-ack-${a.id}`}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-slate-800 hover:border-emerald-500 hover:text-emerald-300 text-slate-300 rounded-sm">
                  <CheckCircle size={12}/> Acknowledge
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
