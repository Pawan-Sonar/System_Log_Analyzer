import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { FilePdf, FileCsv, Play } from "@phosphor-icons/react";
import { api, apiError } from "../lib/api";

export default function Reports() {
  const [items, setItems] = useState([]);
  const [running, setRunning] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get("/reports");
      setItems(data.items || []);
    } catch (err) { toast.error(apiError(err)); }
  };
  useEffect(() => { load(); }, []);

  const run = async () => {
    setRunning(true);
    try {
      const { data } = await api.get("/analytics/run");
      toast.success(`Analysis complete — risk ${data.risk_score}/100 (${data.risk_level}).`);
      load();
    } catch (err) {
      toast.error(apiError(err));
    } finally { setRunning(false); }
  };

  const dl = async (kind) => {
    const url = kind === "pdf" ? "/reports/pdf" : `/reports/csv/${kind}`;
    try {
      const res = await api.get(url, { responseType: "blob" });
      const blob = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = blob;
      a.download = kind === "pdf" ? "security-report.pdf" : `${kind}.csv`;
      a.click(); URL.revokeObjectURL(blob);
    } catch (err) { toast.error(apiError(err)); }
  };

  return (
    <div className="space-y-5 anim-fade" data-testid="reports-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <div className="section-label">// Deliverables</div>
          <h1 className="font-mono text-3xl font-bold tracking-tight">Reports & Exports</h1>
        </div>
        <button onClick={run} disabled={running} data-testid="run-analysis-btn"
          className="flex items-center gap-2 px-4 py-2 text-xs font-mono uppercase tracking-widest bg-blue-500 hover:bg-blue-400 text-black rounded-sm font-bold disabled:opacity-50">
          <Play size={14}/> {running ? "Analyzing…" : "Run Analysis"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActionCard
          testid="action-pdf"
          title="PDF Threat Report" subtitle="Executive summary, KPIs, top threats, recommendations"
          icon={FilePdf} onClick={() => dl("pdf")} accent="#EF4444" cta="Generate PDF"
        />
        <ActionCard
          testid="action-csv-logs"
          title="Logs CSV" subtitle="All ingested log entries with timestamps and outcomes"
          icon={FileCsv} onClick={() => dl("logs")} accent="#10B981" cta="Download CSV"
        />
        <ActionCard
          testid="action-csv-alerts"
          title="Alerts CSV" subtitle="Detected alerts with severity and MITRE mapping"
          icon={FileCsv} onClick={() => dl("alerts")} accent="#F59E0B" cta="Download CSV"
        />
      </div>

      <div className="card" data-testid="reports-history">
        <div className="px-4 py-3 border-b border-slate-800 section-label">Analysis History</div>
        <table className="w-full text-xs">
          <thead className="bg-[#070708] border-b border-slate-800">
            <tr className="font-mono uppercase tracking-widest text-[10px] text-slate-500">
              {["Date","Risk Score","Level","Logs","Failed","Suspicious IPs","Summary"].map((h) => (
                <th key={h} className="text-left px-4 py-2.5">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-slate-500 font-mono">No reports yet. Run an analysis.</td></tr>}
            {items.map((r) => (
              <tr key={r.id} className="border-b border-slate-900/80">
                <td className="px-4 py-2 font-mono text-slate-300">{(r.report_date || "").replace("T", " ").slice(0, 19)}</td>
                <td className="px-4 py-2 font-mono text-slate-200">{r.risk_score}</td>
                <td className="px-4 py-2 font-mono uppercase text-xs" style={{ color: ({critical:"#FCA5A5",high:"#FCD34D",medium:"#93C5FD",low:"#6EE7B7"}[r.risk_level]) }}>{r.risk_level}</td>
                <td className="px-4 py-2 font-mono text-slate-400">{r.total_logs}</td>
                <td className="px-4 py-2 font-mono text-slate-400">{r.failed_logins}</td>
                <td className="px-4 py-2 font-mono text-slate-400">{r.suspicious_ips}</td>
                <td className="px-4 py-2 text-slate-400">{r.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ActionCard({ title, subtitle, icon: Icon, onClick, accent, cta, testid }) {
  return (
    <div className="card p-5 flex flex-col justify-between gap-4" data-testid={testid}>
      <div>
        <Icon size={28} weight="duotone" style={{ color: accent }} />
        <h3 className="font-mono font-bold text-base mt-3 mb-1">{title}</h3>
        <p className="text-xs text-slate-400">{subtitle}</p>
      </div>
      <button onClick={onClick}
        className="font-mono text-[10px] uppercase tracking-widest border border-slate-800 hover:border-blue-500 hover:text-blue-300 text-slate-200 px-3 py-2 rounded-sm self-start">
        {cta}
      </button>
    </div>
  );
}
